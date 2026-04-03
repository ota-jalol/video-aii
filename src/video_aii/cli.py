from __future__ import annotations

import argparse
import json

from .analyzer import analyze_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-aii")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_cmd = subparsers.add_parser("analyze", help="Analyze video files in a directory")
    analyze_cmd.add_argument("path", help="Path to scan")
    analyze_cmd.add_argument(
        "--extension",
        action="append",
        default=[],
        help="Limit analysis to one or more extensions, e.g. --extension .mp4",
    )
    analyze_cmd.add_argument("--top-k", type=int, default=5, help="Top largest files to return")
    analyze_cmd.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        ext_filter = {item.lower() for item in args.extension} if args.extension else None
        result = analyze_directory(args.path, extensions=ext_filter, top_k=args.top_k)
        print(json.dumps(result.to_dict(), indent=2 if args.pretty else None, ensure_ascii=False))


if __name__ == "__main__":
    main()
