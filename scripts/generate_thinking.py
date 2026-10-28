#!/usr/bin/env python3
"""给当天那期日报补上“人物思考”。

流程：读 data/editions/<今天>.json 里抓好的 10 条 → 对每条打开原文链接，
抓正文 → 调 DeepSeek（OpenAI 兼容接口）从原文里提炼人物的核心判断和原话
→ 写回 JSON。前端不用改，person_name 等字段一填上，页面就自动显示。

诚实原则（和 v1 一样重要）：
- 只从原文里提炼，不从标题推断。原文打不开、原文里找不到明确表达
  观点的人物，就留空，绝不编一句“他认为”。
- 原话必须逐字校验：key_quote 要在原文里一字不差地出现，否则删掉这句
  原话（只保留提炼出的判断）；人名也要在原文里出现，否则整条思考作废。
- 没有 API key 时直接跳过、正常退出（exit 0），不影响日报本身。

只用 Python 标准库，不用装任何包。

用法：
    # GitHub Actions 里这样跑（key 从 Secret 传进来）：
    DEEPSEEK_API_KEY=sk-... python3 scripts/generate_thinking.py

    # 本地测试（不写仓库数据）：
    python3 scripts/generate_thinking.py --edition /tmp/news-test/2026-10-28.json
    python3 scripts/generate_thinking.py --date 2026-10-28 --api-key sk-...

    # 换成别的 OpenAI 兼容接口（比如通义千问兼容模式）：
    DEEPSEEK_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1 \
    DEEPSEEK_API_KEY=sk-... python3 scripts/generate_thinking.py
"""

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))  # 北京时间

DEFAULT_BASE_URL = "https://api.deepseek.com"
MODEL = "deepseek-chat"
MAX_ARTICLE_CHARS = 8000   # 喂给模型的正文上限，约等于 4000 个 token 以内
MAX_STORIES = 10
SLEEP_BETWEEN_CALLS = 1.0  # 两次 API 调用之间歇 1 秒

TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
DROP_TAGS_RE = re.compile(
    r"<(script|style|nav|footer|header|aside|noscript|iframe|svg)[^>]*>"
    r".*?</\1>", re.S | re.I
)

THINKING_DONE = "已生成人物思考：核心判断与原话均来自原文，原话已逐字校验。"
THINKING_NONE = "未生成人物思考：原文中找不到明确表达观点的人物，未编造。"
THINKING_FETCH_FAIL = "未生成人物思考：原文页面抓取失败。"
THINKING_API_FAIL = "未生成人物思考：AI 调用失败。"

SYSTEM_PROMPT = (
    "你是新闻分析助手。只根据下面提供的文章原文提炼人物思考，绝不编造、"
    "绝不推断文章里没有的东西。输出必须是且只能是一个 JSON 对象，不要输出"
    "任何解释、不要用 markdown 包裹。\n\n"
    "任务：找出这篇文章中最核心的一位人物——必须是文章中明确提到、并且"
    "明确表达过观点或判断的人（接受采访、发声明、演讲、写署名文章都算；"
    "只被顺带提了一句名字、不算）。如果没有这样的人，或者找不到他的明确"
    "观点，返回 {\"person_found\": false}。\n\n"
    "找到人时，返回以下字段（全部用中文写，key_quote 除外）：\n"
    "- person_found: true\n"
    "- person_name: 人名（按原文里的写法）\n"
    "- person_role: 身份，如“英伟达创始人兼 CEO”\n"
    "- thinking_question: 他面临的核心问题，一句话\n"
    "- core_judgment: 他的核心判断，一两句话，写成“他认为：……”的口吻，"
    "但内容必须是原文观点的忠实提炼\n"
    "- reasoning: 推理链，2–4 条，每条一句话，只写原文里能支撑的推理\n"
    "- key_quote: 原文中的一句话，必须从文章里一字不差地抄下来，不许改写、"
    "不许翻译、英文原文就给英文；如果找不到这样一句完整原话，填 null\n"
    "- background: 背景，一两句话\n"
    "- watch_next: 接下来看他做什么，一句话"
)


def clean_article_html(raw_html: str) -> str:
    """去掉脚本、样式、导航等，只留正文文字，压缩空白。"""
    text = DROP_TAGS_RE.sub(" ", raw_html)
    text = TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = WS_RE.sub(" ", text).strip()
    return text


def fetch_article(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read(300_000)  # 最多读 300KB，够了
    text = data.decode("utf-8", errors="ignore")
    return clean_article_html(text)[:MAX_ARTICLE_CHARS]


def norm(s: str) -> str:
    """归一化：压缩空白、统一大小写，方便逐字比对原话和人名。"""
    return WS_RE.sub(" ", s or "").strip().lower()


def quote_in_article(quote: str, article: str) -> bool:
    q, a = norm(quote), norm(article)
    return bool(q) and q in a


def name_in_article(name: str, article: str) -> bool:
    """人名要在原文里出现。英文名查全名，查不到再查姓。"""
    a = norm(article)
    n = norm(name)
    if n and n in a:
        return True
    parts = n.split()
    return len(parts) > 1 and bool(parts[-1]) and parts[-1] in a


def call_llm(api_key: str, base_url: str, title: str, article: str) -> dict:
    user_content = (
        f"文章标题：{title}\n\n文章原文（已截断）：\n{article}\n\n"
        "请按系统提示返回 JSON。"
    )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    content = body["choices"][0]["message"]["content"]
    # 模型偶尔会在 JSON 外加解释，只取第一个 { 到最后一个 } 之间的部分
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("模型没有返回 JSON")
    return json.loads(content[start:end + 1])


def process_story(story: dict, api_key: str, base_url: str) -> str:
    """处理一条新闻，填好人物思考字段。返回状态说明（打日志用）。"""
    url = (story.get("sources") or [{}])[0].get("url", "")
    if not url:
        story["thinking_status"] = THINKING_FETCH_FAIL
        return "没有来源链接，跳过"

    try:
        article = fetch_article(url)
    except Exception as exc:
        story["thinking_status"] = THINKING_FETCH_FAIL
        return f"原文抓取失败：{exc}"
    if len(article) < 200:
        story["thinking_status"] = THINKING_FETCH_FAIL
        return "原文正文太短（可能被反爬挡住），跳过"

    try:
        result = call_llm(api_key, base_url, story.get("title", ""), article)
    except Exception as exc:
        story["thinking_status"] = THINKING_API_FAIL
        return f"AI 调用失败：{exc}"

    if not result.get("person_found") or not result.get("person_name"):
        story["thinking_status"] = THINKING_NONE
        return "原文里没有明确表达观点的人物，留空"

    name = str(result["person_name"]).strip()
    if not name_in_article(name, article):
        story["thinking_status"] = THINKING_NONE
        return f"人名 {name!r} 不在原文里，整条思考作废（防张冠李戴）"

    quote = result.get("key_quote")
    if quote:
        quote = str(quote).strip()
        if not quote_in_article(quote, article):
            print(f"    [warn] 原话不在原文里，已删掉：{quote[:40]}…")
            quote = None
    else:
        quote = None

    story["person_name"] = name
    story["person_role"] = str(result.get("person_role") or "").strip() or None
    story["thinking_question"] = str(result.get("thinking_question") or "").strip() or None
    story["core_judgment"] = str(result.get("core_judgment") or "").strip() or None
    reasoning = result.get("reasoning") or []
    story["reasoning"] = [str(r).strip() for r in reasoning if str(r).strip()][:4]
    story["key_quote"] = quote
    story["background"] = str(result.get("background") or "").strip() or None
    story["watch_next"] = str(result.get("watch_next") or "").strip() or None
    story["thinking_status"] = THINKING_DONE
    return f"已补 {name} 的思考" + ("（带逐字校验的原话）" if quote else "（无可用原话）")


def main() -> int:
    parser = argparse.ArgumentParser(description="给当天那期日报补人物思考")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天（北京时间）")
    parser.add_argument("--edition", default=None, help="直接指定某期 JSON 文件的路径")
    parser.add_argument("--api-key", default=None, help="DeepSeek key，默认读环境变量 DEEPSEEK_API_KEY")
    parser.add_argument("--base-url", default=None,
                        help="API 地址，默认 https://api.deepseek.com，可换 OpenAI 兼容接口")
    parser.add_argument("--limit", type=int, default=MAX_STORIES, help="最多处理几条，默认 10")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        print("[skip] 没有 DEEPSEEK_API_KEY，不生成人物思考（日报本身不受影响）。")
        return 0
    base_url = args.base_url or os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)

    date_str = args.date or datetime.now(CST).strftime("%Y-%m-%d")
    edition_path = Path(args.edition) if args.edition else REPO_ROOT / "data" / "editions" / f"{date_str}.json"
    if not edition_path.exists():
        print(f"[error] 找不到那期文件：{edition_path}，先跑 fetch_daily.py。", file=sys.stderr)
        return 1
    edition = json.loads(edition_path.read_text(encoding="utf-8"))

    done, skipped = 0, 0
    for story in edition.get("stories", [])[: args.limit]:
        if story.get("person_name"):
            print(f"[{story['rank']}] 已有思考，跳过")
            skipped += 1
            continue
        print(f"[{story['rank']}] {story.get('title', '')[:40]}…")
        try:
            msg = process_story(story, api_key, base_url)
        except Exception as exc:  # 单条失败不影响其他条
            story["thinking_status"] = THINKING_API_FAIL
            msg = f"处理异常：{exc}"
        print(f"    {msg}")
        if story.get("person_name"):
            done += 1
        else:
            skipped += 1
        time.sleep(SLEEP_BETWEEN_CALLS)

    if done:
        edition["note"] = "人物思考由 AI 根据原文提炼，原话已在原文中逐字校验；找不到人物原话的条目会留空、不编造。"
    edition_path.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 写入 {edition_path}（补上 {done} 条思考，{skipped} 条留空）")

    # 同步更新 latest.json：只有按默认路径跑（没指定 --edition）时才做，
    # 指定了 --edition 的本地测试绝不动仓库里的 latest.json。
    latest = REPO_ROOT / "data" / "latest.json"
    if not args.edition and latest.exists():
        try:
            latest_edition = json.loads(latest.read_text(encoding="utf-8"))
            if latest_edition.get("date") == edition.get("date"):
                latest.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[ok] 更新 {latest}")
        except Exception as exc:
            print(f"[warn] latest.json 更新失败：{exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
