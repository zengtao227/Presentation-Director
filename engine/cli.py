"""Command line for the engine; uses the same Engine methods as the MCP server."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from engine.core import Engine, EngineError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="presentation-director")
    parser.add_argument(
        "--workspace", type=Path, help="任务存放目录（默认 文档/Presentation Director）"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("start", help="新建任务")
    p.add_argument("--request", required=True)
    p.add_argument("--topic", default="")
    p.add_argument("--source", action="append", default=[])
    p = sub.add_parser("confirm", help="打开确认页并等待用户点确认")
    p.add_argument("task")
    p.add_argument("--no-open", action="store_true")
    p.add_argument("--timeout", type=int, default=3600)
    p = sub.add_parser("status")
    p.add_argument("task")
    p = sub.add_parser("generate")
    p.add_argument("task")
    p.add_argument("--spec", type=Path, required=True)
    p = sub.add_parser("check")
    p.add_argument("task")
    p.add_argument("--version")
    p = sub.add_parser("export")
    p.add_argument("task")
    p.add_argument("--version")
    p.add_argument("--dest")
    args = parser.parse_args(argv)

    eng = Engine(args.workspace)
    try:
        if args.cmd == "start":
            result = eng.start_task(args.request, args.topic, args.source)
        elif args.cmd == "confirm":
            opened = eng.open_confirmation(args.task, open_browser=not args.no_open)
            print(f"确认页：{opened['url']}", file=sys.stderr)
            deadline = time.monotonic() + args.timeout
            while not eng.status(args.task)["confirmed"]:
                if time.monotonic() > deadline:
                    raise EngineError("等待确认超时")
                time.sleep(1)
            eng.close_confirmation(args.task)
            result = eng.status(args.task)
        elif args.cmd == "status":
            result = eng.status(args.task)
        elif args.cmd == "generate":
            result = eng.generate(args.task, args.spec.read_text(encoding="utf-8"))
        elif args.cmd == "check":
            result = eng.render_check(args.task, args.version)
        else:
            result = eng.export(args.task, args.version, args.dest)
    except EngineError as err:
        print(str(err), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
