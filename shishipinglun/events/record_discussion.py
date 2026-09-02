"""把 Codex 在对话中给出的讨论回复写回事件中心，前端即可看到。

用法：
  python3 record_discussion.py --event <事件ID> --comment <评论ID> --text "回复内容"
  python3 record_discussion.py --event <事件ID> --comment <评论ID> --file /path/reply.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from . import db
except ImportError:  # 直接以脚本方式运行 python3 record_discussion.py 时
    import db


def main() -> int:
    ap = argparse.ArgumentParser(description="将助手讨论回复写入事件中心")
    ap.add_argument("--event", required=True, help="事件 ID")
    ap.add_argument("--comment", required=True, help="评论 ID")
    ap.add_argument("--text", default="", help="回复文本")
    ap.add_argument("--file", default="", help="从文件读取回复文本")
    args = ap.parse_args()

    text = args.text
    if args.file:
        text = Path(args.file).read_text(encoding="utf-8")
    text = text.strip()
    if not text:
        print("错误：--text 或 --file 必须提供非空回复内容", file=sys.stderr)
        return 2

    data = db.load_db()
    comment = None
    for cm in data["comments"]:
        if cm["id"] == args.comment and cm["event_id"] == args.event:
            comment = cm
            break
    if comment is None:
        print(f"错误：找不到事件 {args.event} 下的评论 {args.comment}", file=sys.stderr)
        return 1
    comment.setdefault("discussion", []).append(
        {"role": "assistant", "text": text, "at": db.now_iso()}
    )
    comment["want_discussion"] = False
    db.save_db(data)
    print(f"已写入讨论回复（事件 {args.event} / 评论 {args.comment}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
