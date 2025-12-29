from __future__ import annotations
import logging
import uuid

from config import RunConfig, validate_config
from scanner import get_files
from naming import bucket_for
from fs_ops import ensure_dir, next_available, do_copy, do_move
from plan_io import PlanWriter

def run_sort(cfg: RunConfig, logger: logging.Logger) -> int:
    validate_config(cfg)

    run_id = uuid.uuid4().hex[:12]
    plan_writer = None

    if cfg.plan_out is not None:
        cfg.plan_out.parent.mkdir(parents=True, exist_ok=True)
        plan_fp = open(cfg.plan_out, "a", encoding="utf-8", newline="\n")
        plan_writer = PlanWriter(plan_fp, run_id, fsync=cfg.plan_fsync)
        plan_writer.run_start(cfg.to_dict())
        logger.info("plan -> %s", cfg.plan_out)
    
    scanned = moved = copied = skipped = failed = 0

    try:
        for f in get_files(cfg.src, cfg.recursive):
            scanned += 1
            try:
                st = f.stat()
                size_bytes = st.st_size
                ext = f.suffix.lower().lstrip(".") or "no_ext"
                if cfg.min_size_kb > 0 and size_bytes < cfg.min_size_kb * 1024:
                    skipped += 1
                    if plan_writer:
                        plan_writer.item({
                            "op": "SKIP",
                            "status": "SKIPPED",
                            "src": str(f),
                            "dst": None,
                            "size_bytes": size_bytes,
                            "ext": ext,
                            "reason": "size_too_small",
                            "dry_run": cfg.dry_run,
                        })
                    continue
                if cfg.only_ext and ext not in cfg.only_ext:
                    skipped += 1
                    if plan_writer:
                        plan_writer.item({
                            "op": "SKIP",
                            "status": "SKIPPED",
                            "src": str(f),
                            "dst": None,
                            "size_bytes": size_bytes,
                            "ext": ext,
                            "reason": "not in only_set",
                            "dry_run": cfg.dry_run,
                        })
                    continue

                if cfg.exclude_ext and ext in cfg.exclude_ext:
                    skipped += 1
                    if plan_writer:
                        plan_writer.item({
                            "op": "SKIP",
                            "status": "SKIPPED",
                            "src": str(f),
                            "dst": None,
                            "size_bytes": size_bytes,
                            "ext": ext,
                            "reason": "in exclude_ext",
                            "dry_run": cfg.dry_run,
                        })
                    continue

                bucket = bucket_for(f, st, cfg.mode)
                target_dir = cfg.dst / bucket
                ensure_dir(target_dir)
                target_path = next_available(target_dir / f.name)

                if cfg.dry_run:
                    if plan_writer:
                        plan_writer.item({
                            "op": cfg.action.upper(),
                            "status": "DRY",
                            "src": str(f),
                            "dst": str(target_path),
                            "mode": cfg.mode,
                            "bucket": bucket,
                            "size_bytes": size_bytes,
                            "ext": ext,
                            "reason": "dry_run",
                            "dry_run": True,
                        })
                    continue

                if cfg.action == "copy":
                    do_copy(f, target_path)
                    copied += 1
                    op = "COPY"
                else:
                    do_move(f, target_path)
                    moved += 1
                    op = "MOVE"

                logger.debug("[%s] %s -> %s", op, f, target_path)
                if plan_writer:
                    plan_writer.item({
                        "op": op,
                        "status": "OK",
                        "src": str(f),
                        "dst": str(target_path),
                        "mode": cfg.mode,
                        "bucket": bucket,
                        "size_bytes": size_bytes,
                        "ext": ext,
                        "reason": "matched",
                        "dry_run": False,
                    })
            except Exception as e:
                failed += 1
                logger.error("[FAIL] %s (%s)", f, e)
                if plan_writer:
                    plan_writer.item({
                        "op": "FAIL",
                        "status": "ERROR",
                        "wanted_op": cfg.action.upper(),
                        "src": str(f),
                        "dst": None,
                        "error": f"{type(e).__name__}: {e}",
                    })
    finally:
        summary = {
            "scanned": scanned,
            "moved": moved,
            "copied": copied,
            "skipped": skipped,
            "failed": failed,
        }
        logger.info("summary: %s", summary)
        if plan_writer:
            plan_writer.run_end(summary)
            plan_writer.fp.close()
    return 0 if failed == 0 else 2
