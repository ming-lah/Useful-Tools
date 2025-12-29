import argparse
import logging
from pathlib import Path

from config import RunConfig, parse_ext_list
from logger_utils import setup_logging
from runner import run_sort

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Day01 practical file automation tool")
    ap.add_argument("--src", required=True, help="source directory")
    ap.add_argument("--dst", required=True, help="destination directory")

    ap.add_argument("--recursive", action="store_true", help="scan recursively")
    ap.add_argument("--mode", choices=["ext", "date"], default="ext", help="bucket mode")
    ap.add_argument("--action", choices=["copy", "move"], default="move", help="copy or move")
    ap.add_argument("--dry-run", action="store_true", help="plan only, no filesystem changes")

    ap.add_argument("--only-ext", default="", help="only include these extensions: jpg,png")
    ap.add_argument("--exclude-ext", default="", help="exclude these extensions: tmp,part")
    ap.add_argument("--min-size-kb", type=int, default=0, help="skip files smaller than this")

    ap.add_argument("--plan-out", default="", help="path to plan.jsonl (JSON Lines)")
    ap.add_argument("--plan-fsync", action="store_true", help="fsync every plan line (slower but safer)")

    ap.add_argument("--log-file", default="", help="log file path (optional)")
    ap.add_argument("--log-level", default="INFO", help="console log level: DEBUG/INFO/WARNING/ERROR")
    return ap

def main() -> None:
    ap = build_parser()
    args = ap.parse_args()

    src = Path(args.src)
    dst = Path(args.dst)

    plan_out = Path(args.plan_out) if args.plan_out else (dst / "logs" / "plan.jsonl")
    log_file = Path(args.log_file) if args.log_file else (dst / "logs" / "run.log")

    console_level = getattr(logging, args.log_level.upper(), logging.INFO)

    cfg = RunConfig(
        src=src,
        dst=dst,
        recursive=bool(args.recursive),
        mode=args.mode,
        action=args.action,
        dry_run=bool(args.dry_run),
        only_ext=parse_ext_list(args.only_ext),
        exclude_ext=parse_ext_list(args.exclude_ext),
        min_size_kb=int(args.min_size_kb),
        plan_out=plan_out,
        plan_fsync=bool(args.plan_fsync),
        log_file=log_file,
        console_level=console_level,
        file_level=logging.DEBUG,
    )

    logger = setup_logging(cfg.log_file, console_level=cfg.console_level, file_level=cfg.file_level)
    rc = run_sort(cfg, logger)
    raise SystemExit(rc)

if __name__ == "__main__":
    main()
