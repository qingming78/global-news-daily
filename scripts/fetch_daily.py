#!/usr/bin/env python3
"""每日抓取公开 RSS，生成一期《全球大事日报》JSON。

只用 Python 标准库（urllib / xml.etree / json），不需要 pip 安装，
所以 GitHub Actions 里可以直接跑。

诚实原则（v1）：
- 只写标题、摘要、来源链接这些 RSS 里本来就有的东西。
- 人物思考字段（person_name / core_judgment / key_quote 等）留空，
  并标上 thinking_status = "待补充人物思考"，绝不从标题推断
  某个人说了什么、想了什么。想补人物思考，等有了 LLM API key
  再按 README 里的“以后怎么加 AI 生成”那一节做。

用法：
    python3 scripts/fetch_daily.py                 # 生成今天（北京时间）那期
    python3 scripts/fetch_daily.py --date 2026-10-29
    python3 scripts/fetch_daily.py --out-dir /tmp/test-output   # 只写到指定目录
"""

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))  # 北京时间

# 每个源一个默认分类。AI 类来源排在前面，抓取时优先。
FEEDS = [
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "AI科技"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", "AI科技"),
    ("Hacker News", "https://hnrss.org/frontpage", "AI科技"),
    ("Wired", "https://www.wired.com/feed/rss", "AI科技"),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "AI科技"),
    ("BBC 科技", "https://feeds.bbci.co.uk/news/technology/rss.xml", "科学气候"),
    ("BBC 国际", "https://feeds.bbci.co.uk/news/world/rss.xml", "政治外交"),
]

AI_KEYWORDS = [
    "artificial intelligence", "nvidia", "英伟达", "openai", "anthropic",
    "google", "deepmind", "chatgpt", "大模型", "模型", "芯片",
    "算力", "machine learning", "机器学习", "deepseek", "机器人",
    "自动驾驶", "microsoft", "微软", "apple", "苹果",
]

MAX_STORIES = 10
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean_text(raw: str, limit: int = 140) -> str:
    """去掉 HTML 标签、解码实体、压缩空白，截断到 limit 字。"""
    text = html.unescape(TAG_RE.sub(" ", raw or ""))
    text = WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


WORD_KEYWORDS = ["ai", "llm", "gpu", "chip", "meta", "robot"]


def ai_score(text: str) -> int:
    low = text.lower()
    score = 0
    for kw in AI_KEYWORDS:
        if kw.lower() in low:
            score += 1
    # 短词必须按完整单词匹配，否则 "ai" 会误中 said / again / daily 这种词
    for kw in WORD_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", low):
            score += 1
    return score


def fetch_feed(url: str, timeout: int = 20) -> list[dict]:
    req = urllib.request.Request(
        url, headers={"User-Agent": "global-news-free/1.0 (+github-actions)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    items = []
    # RSS 2.0: channel/item；Atom: entry（顺带兼容）
    for el in root.iter("item"):
        items.append({
            "title": (el.findtext("title") or "").strip(),
            "link": (el.findtext("link") or "").strip(),
            "summary": clean_text(el.findtext("description") or ""),
            "pub": (el.findtext("pubDate") or "").strip(),
        })
    if not items:
        for el in root.iter("{http://www.w3.org/2005/Atom}entry"):
            link = ""
            for l in el.findall("{http://www.w3.org/2005/Atom}link"):
                if l.get("rel") in (None, "alternate"):
                    link = l.get("href") or ""
                    break
            items.append({
                "title": (el.findtext("{http://www.w3.org/2005/Atom}title") or "").strip(),
                "link": link.strip(),
                "summary": clean_text(el.findtext("{http://www.w3.org/2005/Atom}summary") or ""),
                "pub": (el.findtext("{http://www.w3.org/2005/Atom}updated") or "").strip(),
            })
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="抓取 RSS，生成一期日报 JSON")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天（北京时间）")
    parser.add_argument("--out-dir", default=None,
                        help="JSON 写到哪里，默认 <仓库>/data/editions；同时更新 data/latest.json")
    parser.add_argument("--max", type=int, default=MAX_STORIES, help="最多几条，默认 10")
    args = parser.parse_args()

    date_str = args.date or datetime.now(CST).strftime("%Y-%m-%d")
    out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "data" / "editions"
    out_dir.mkdir(parents=True, exist_ok=True)

    seen_links, seen_titles, candidates = set(), set(), []
    for name, url, category in FEEDS:
        try:
            items = fetch_feed(url)
        except Exception as exc:  # 单个源失败不影响整期
            print(f"[warn] {name} 抓取失败：{exc}", file=sys.stderr)
            continue
        print(f"[ok] {name}：{len(items)} 条")
        for it in items:
            if not it["title"] or not it["link"]:
                continue
            link = it["link"].split("#")[0]
            title_key = re.sub(r"\W+", "", it["title"].lower())
            if link in seen_links or title_key in seen_titles:
                continue
            seen_links.add(link)
            seen_titles.add(title_key)
            text = f"{it['title']} {it['summary']}"
            score = ai_score(text)
            candidates.append({
                "title": it["title"],
                "summary": it["summary"] or it["title"],
                "link": link,
                "category": "AI科技" if score >= 2 else category,
                "score": score,
                "pub": it["pub"],
            })

    if not candidates:
        print("[error] 所有 RSS 源都没有抓到内容，不写文件。", file=sys.stderr)
        return 1

    # AI 优先，但保留多样性：最多 6 条 AI，再补最多 4 条非 AI 类别，
    # 按类别轮取（BBC 国际→政治外交、BBC 科技→科学气候），避免被一个源占满；
    # 不够时互相补足。
    ai_items = [c for c in candidates if c["score"] >= 2]
    non_ai_items = [c for c in candidates if c["category"] != "AI科技"]
    by_cat: dict[str, list] = {}
    for c in non_ai_items:
        by_cat.setdefault(c["category"], []).append(c)
    diverse: list = []
    while len(diverse) < 4 and any(by_cat.values()):
        for cat in list(by_cat):
            if by_cat[cat] and len(diverse) < 4:
                diverse.append(by_cat[cat].pop(0))
    picked = ai_items[:6] + diverse
    if len(picked) < args.max:
        rest = [c for c in candidates if c not in picked]
        picked += rest[: args.max - len(picked)]
    picked = picked[: args.max]

    stories = []
    for i, c in enumerate(picked, start=1):
        stories.append({
            "rank": i,
            "category": c["category"],
            "title": c["title"],
            "summary": c["summary"],
            # ---- v1 不生成人物思考：以下字段留空，只标状态 ----
            "person_name": None,
            "person_role": None,
            "thinking_question": None,
            "core_judgment": None,
            "reasoning": [],
            "key_quote": None,
            "background": None,
            "watch_next": None,
            "thinking_status": "待补充人物思考：v1 只抓取标题与摘要，未生成人物思考，请勿把标题推断当作人物原话。",
            "sources": [{"title": c["title"], "url": c["link"]}],
            "images": [],
        })

    edition = {
        "date": date_str,
        "generated_at": datetime.now(CST).isoformat(timespec="seconds"),
        "note": "由 GitHub Actions 每日自动抓取公开 RSS 生成。人物思考字段待补充（见 README），请勿把标题推断当作人物原话。",
        "sample": False,
        "stories": stories,
    }

    edition_path = out_dir / f"{date_str}.json"
    tmp = edition_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(edition_path)
    print(f"[ok] 写入 {edition_path}（{len(stories)} 条）")

    # 同步更新 latest.json（只有写到默认目录时才更新仓库里的 latest）
    if not args.out_dir:
        latest = REPO_ROOT / "data" / "latest.json"
        latest.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ok] 更新 {latest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
