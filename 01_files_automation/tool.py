import argparse
import logging
from pathlib import Path

from config import RunConfig, parse_ext_list
from logger_utils import setup_logging
from runner import run_sort, run_replay, run_undo


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="practical file automation tool (with plan replay/undo)")

    # normal mode needs these; replay/undo don't
    ap.add_argument("--src", default="", help="source directory (normal run)")
    ap.add_argument("--dst", default="", help="destination directory (normal run)")

    ap.add_argument("--recursive", action="store_true", help="scan recursively (normal run)")
    ap.add_argument("--mode", choices=["ext", "date"], default="ext", help="bucket mode (normal run)")
    ap.add_argument("--action", choices=["copy", "move"], default="move", help="copy or move (normal run)")
    ap.add_argument("--dry-run", action="store_true", help="plan only, no filesystem changes")

    ap.add_argument("--only-ext", default="", help="only include these extensions: jpg,png")
    ap.add_argument("--exclude-ext", default="", help="exclude these extensions: tmp,part")
    ap.add_argument("--min-size-kb", type=int, default=0, help="skip files smaller than this")

    # new: conflict + dedupe
    ap.add_argument(
        "--on-conflict",
        choices=["rename", "skip", "overwrite", "fail"],
        default="rename",
        help="when dst exists: rename/skip/overwrite/fail",
    )
    ap.add_argument("--dedupe", action="store_true", help="skip files whose content already exists under dst")

    # plan infra
    ap.add_argument("--plan-out", default="", help="path to output plan.jsonl (JSON Lines)")
    ap.add_argument("--plan-fsync", action="store_true", help="fsync every plan line (slower but safer)")

    # new: replay/undo
    mx = ap.add_mutually_exclusive_group()
    mx.add_argument("--replay", default="", help="replay a DRY plan.jsonl to execute actions")
    mx.add_argument("--undo", default="", help="undo a plan.jsonl (revert MOVE, trash COPY outputs)")

    ap.add_argument("--trash-dir", default="", help="undo: where to put removed COPY outputs (default: <plan_dir>/.undo_trash)")

    ap.add_argument("--log-file", default="", help="log file path (optional)")
    ap.add_argument("--log-level", default="INFO", help="console log level: DEBUG/INFO/WARNING/ERROR")
    return ap


def _default_plan_out_for_normal(dst: Path) -> Path:
    return dst / "logs" / "plan.jsonl"


def _default_log_file_for_normal(dst: Path) -> Path:
    return dst / "logs" / "run.log"


def _default_plan_out_for_plan(plan_in: Path, suffix: str) -> Path:
    # e.g. plan_replay.jsonl / plan_undo.jsonl
    return plan_in.with_name(f"{plan_in.stem}_{suffix}.jsonl")


def _default_log_file_for_plan(plan_in: Path, suffix: str) -> Path:
    return plan_in.with_name(f"{plan_in.stem}_{suffix}.log")


def main() -> None:
    ap = build_parser()
    args = ap.parse_args()

    console_level = getattr(logging, args.log_level.upper(), logging.INFO)

    # -----------------------
    # replay mode
    # -----------------------
    if args.replay:
        plan_in = Path(args.replay)
        plan_out = Path(args.plan_out) if args.plan_out else _default_plan_out_for_plan(plan_in, "replay")
        log_file = Path(args.log_file) if args.log_file else _default_log_file_for_plan(plan_in, "replay")
        logger = setup_logging(log_file, console_level=console_level, file_level=logging.DEBUG)

        # optional dedupe root: if user provides --dst, we use it; else None
        dedupe_root = Path(args.dst) if args.dst else None

        rc = run_replay(
            plan_in,
            logger,
            on_conflict=args.on_conflict,
            dedupe=bool(args.dedupe),
            dry_run=bool(args.dry_run),
            plan_out=plan_out,
            plan_fsync=bool(args.plan_fsync),
            dedupe_root=dedupe_root,
        )
        raise SystemExit(rc)

    # -----------------------
    # undo mode
    # -----------------------
    if args.undo:
        plan_in = Path(args.undo)
        plan_out = Path(args.plan_out) if args.plan_out else _default_plan_out_for_plan(plan_in, "undo")
        log_file = Path(args.log_file) if args.log_file else _default_log_file_for_plan(plan_in, "undo")
        logger = setup_logging(log_file, console_level=console_level, file_level=logging.DEBUG)

        trash_dir = Path(args.trash_dir) if args.trash_dir else None

        rc = run_undo(
            plan_in,
            logger,
            on_conflict=args.on_conflict,
            dry_run=bool(args.dry_run),
            trash_dir=trash_dir,
            plan_out=plan_out,
            plan_fsync=bool(args.plan_fsync),
        )
        raise SystemExit(rc)

    # -----------------------
    # normal mode
    # -----------------------
    if not args.src or not args.dst:
        ap.error("--src and --dst are required unless you use --replay or --undo")

    src = Path(args.src)
    dst = Path(args.dst)

    plan_out = Path(args.plan_out) if args.plan_out else _default_plan_out_for_normal(dst)
    log_file = Path(args.log_file) if args.log_file else _default_log_file_for_normal(dst)

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
        on_conflict=args.on_conflict,
        dedupe=bool(args.dedupe),
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
