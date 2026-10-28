#!/usr/bin/env python3
"""每天一位权威人物：从当天抓好的 10 条里选出一位，写成当期特写。

跑在 fetch_daily.py（抓 10 条）+ generate_thinking.py（补人物思考）之后。
只用 Python 标准库。

选人规则（公开、可解释）：
- 必须有真实人物（person_name 非空），否则不参与评选；
- 有逐字校验过的原话（key_quote 非空）+3 分；
- AI科技类别 +2 分；
- 推理链每条 +1 分（最多 4 分）；
- 有背景介绍 +1 分；
- 同分时取 rank 更靠前（RSS 优先级更高）的那条。
- 如果当天没有任何一条有人物思考，就取 rank 1 的那条兜底
  （页面会显示“待补充人物思考”，但日报不断更）。

输出：
- 把当期 data/editions/<今天>.json 改写为只含当选 1 条的特写，
  并同步更新 data/latest.json；
- 把当选者追加到 data/archive.json（往期档案：日期、人物、标题），
  去重（同一天只保留一条）。

用法：
    python3 scripts/pick_feature.py                  # 处理今天那期
    python3 scripts/pick_feature.py --date 2026-10-28
    python3 scripts/pick_feature.py --edition /tmp/x/2026-10-28.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CST = timezone(timedelta(hours=8))  # 北京时间


def score(story: dict) -> tuple[int, int]:
    """返回 (分数, -rank)，分数高者胜，同分 rank 小者胜。"""
    if not story.get("person_name"):
        return (-1, 0)
    points = 0
    if story.get("key_quote"):
        points += 3
    if story.get("category") == "AI科技":
        points += 2
    points += min(len(story.get("reasoning") or []), 4)
    if story.get("background"):
        points += 1
    return (points, -int(story.get("rank") or 99))


def main() -> int:
    parser = argparse.ArgumentParser(description="从当天 10 条里选出一位人物特写")
    parser.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天（北京时间）")
    parser.add_argument("--edition", default=None, help="直接指定某期 JSON 文件的路径")
    parser.add_argument("--archive", default=None, help="档案文件路径，默认 <仓库>/data/archive.json")
    args = parser.parse_args()

    date_str = args.date or datetime.now(CST).strftime("%Y-%m-%d")
    edition_path = Path(args.edition) if args.edition else REPO_ROOT / "data" / "editions" / f"{date_str}.json"
    if not edition_path.exists():
        print(f"[error] 找不到那期文件：{edition_path}，先跑 fetch_daily.py。", file=sys.stderr)
        return 1
    edition = json.loads(edition_path.read_text(encoding="utf-8"))
    stories = edition.get("stories") or []
    if not stories:
        print("[error] 这期没有内容，无法选人。", file=sys.stderr)
        return 1

    with_person = [s for s in stories if s.get("person_name")]
    if with_person:
        picked = max(with_person, key=score)
        reason = f"评分 {score(picked)[0]} 分（有原话/类别/推理链加权）"
    else:
        picked = sorted(stories, key=lambda s: int(s.get("rank") or 99))[0]
        reason = "当天没有一条有人物思考，取 rank 1 兜底"
    print(f"[ok] 今天的人物：{picked.get('person_name') or '（暂无人物）'}"
          f"——{picked.get('title', '')[:40]}…（{reason}）")

    edition["stories"] = [picked]
    edition["format"] = "daily-thinker"
    edition["note"] = "每天一位权威人物：每天只读一个人对一件事的深度思考，内容来自公开采访、演讲或署名文章，原话均逐字引用自原文。"
    edition_path.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 写入 {edition_path}（1 条特写）")

    # 同步更新 latest.json（只有按默认路径跑时才动仓库里的 latest）
    if not args.edition:
        latest = REPO_ROOT / "data" / "latest.json"
        latest.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ok] 更新 {latest}")

    # 往期档案：同一天只保留一条（重复跑会覆盖，不会重复记）
    archive_path = Path(args.archive) if args.archive else REPO_ROOT / "data" / "archive.json"
    archive = []
    if archive_path.exists():
        try:
            archive = json.loads(archive_path.read_text(encoding="utf-8"))
        except Exception:
            archive = []
    entry = {
        "date": edition.get("date", date_str),
        "person_name": picked.get("person_name"),
        "person_role": picked.get("person_role"),
        "title": picked.get("title"),
        "category": picked.get("category"),
        "core_judgment": picked.get("core_judgment"),
    }
    archive = [e for e in archive if e.get("date") != entry["date"]]
    archive.insert(0, entry)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 更新档案 {archive_path}（共 {len(archive)} 期）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
