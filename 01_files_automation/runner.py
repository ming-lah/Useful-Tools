from __future__ import annotations
import hashlib
import logging
import uuid
from pathlib import Path
from typing import Dict, Tuple, Optional

from config import RunConfig, validate_config
from scanner import get_files
from naming import bucket_for
from fs_ops import ensure_dir, resolve_dst, remove_if_exists, do_copy, do_move
from plan_io import PlanWriter, read_json


Sig = Tuple[int, str]  # (size_bytes, sha256)


def _sha256_file(p: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _sig_for(p: Path) -> Sig:
    st = p.stat()
    return st.st_size, _sha256_file(p)


def _should_skip_dedupe_path(p: Path) -> bool:
    parts = set(x.lower() for x in p.parts)
    if "logs" in parts:
        return True
    if ".undo_trash" in parts:
        return True
    return False


def build_dedupe_index(dst_root: Path, logger: logging.Logger) -> Dict[Sig, Path]:
    """
    Scan dst_root and build signature index for --dedupe.
    """
    idx: Dict[Sig, Path] = {}
    if not dst_root.exists():
        return idx

    hashed = 0
    for p in get_files(dst_root, True):
        if _should_skip_dedupe_path(p):
            continue
        try:
            sig = _sig_for(p)
            idx.setdefault(sig, p)
            hashed += 1
            if hashed % 500 == 0:
                logger.info("dedupe index: hashed=%d ...", hashed)
        except Exception:
            continue

    logger.info("dedupe index ready: files=%d", len(idx))
    return idx


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

    dedupe_idx: Dict[Sig, Path] = {}
    if cfg.dedupe:
        logger.info("building dedupe index under dst=%s ...", cfg.dst)
        dedupe_idx = build_dedupe_index(cfg.dst, logger)

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
                            "reason": "not_in_only_ext",
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
                            "reason": "in_exclude_ext",
                            "dry_run": cfg.dry_run,
                        })
                    continue

                # dedupe (content)
                sig: Optional[Sig] = None
                sha256: Optional[str] = None
                if cfg.dedupe:
                    sig = _sig_for(f)
                    sha256 = sig[1]
                    if sig in dedupe_idx:
                        skipped += 1
                        if plan_writer:
                            plan_writer.item({
                                "op": "SKIP",
                                "status": "SKIPPED",
                                "src": str(f),
                                "dst": None,
                                "size_bytes": size_bytes,
                                "ext": ext,
                                "reason": "dedupe_duplicate_of",
                                "sha256": sha256,
                                "duplicate_of": str(dedupe_idx[sig]),
                                "dry_run": cfg.dry_run,
                            })
                        continue

                bucket = bucket_for(f, st, cfg.mode)
                target_dir = cfg.dst / bucket
                ensure_dir(target_dir)

                dst_base = target_dir / f.name
                dst_final, conflict_decision = resolve_dst(dst_base, cfg.on_conflict)

                if conflict_decision == "skip":
                    skipped += 1
                    if plan_writer:
                        plan_writer.item({
                            "op": "SKIP",
                            "status": "SKIPPED",
                            "src": str(f),
                            "dst": str(dst_base),
                            "dst_final": str(dst_final),
                            "mode": cfg.mode,
                            "bucket": bucket,
                            "size_bytes": size_bytes,
                            "ext": ext,
                            "reason": "conflict_skip",
                            "on_conflict": cfg.on_conflict,
                            "dry_run": cfg.dry_run,
                        })
                    continue

                if cfg.dry_run:
                    if plan_writer:
                        plan_writer.item({
                            "op": cfg.action.upper(),
                            "status": "DRY",
                            "src": str(f),
                            "dst": str(dst_final),
                            "dst_base": str(dst_base),
                            "conflict": conflict_decision,
                            "on_conflict": cfg.on_conflict,
                            "mode": cfg.mode,
                            "bucket": bucket,
                            "size_bytes": size_bytes,
                            "ext": ext,
                            "sha256": sha256,
                            "reason": "dry_run",
                            "dry_run": True,
                            "dedupe": cfg.dedupe,
                        })
                    # important: dedupe should affect later items even in dry-run
                    if cfg.dedupe and sig is not None:
                        dedupe_idx[sig] = Path(dst_final)
                    continue

                # apply
                dst_final.parent.mkdir(parents=True, exist_ok=True)
                if conflict_decision == "overwrite":
                    remove_if_exists(dst_final)

                if cfg.action == "copy":
                    do_copy(f, dst_final)
                    copied += 1
                    op = "COPY"
                else:
                    do_move(f, dst_final)
                    moved += 1
                    op = "MOVE"

                logger.debug("[%s] %s -> %s", op, f, dst_final)
                if plan_writer:
                    plan_writer.item({
                        "op": op,
                        "status": "OK",
                        "src": str(f),
                        "dst": str(dst_final),
                        "dst_base": str(dst_base),
                        "conflict": conflict_decision,
                        "on_conflict": cfg.on_conflict,
                        "mode": cfg.mode,
                        "bucket": bucket,
                        "size_bytes": size_bytes,
                        "ext": ext,
                        "sha256": sha256,
                        "reason": "matched",
                        "dry_run": False,
                        "dedupe": cfg.dedupe,
                    })

                if cfg.dedupe and sig is not None:
                    dedupe_idx[sig] = dst_final

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


def run_replay(
    plan_path: Path,
    logger: logging.Logger,
    *,
    on_conflict: str = "rename",
    dedupe: bool = False,
    dry_run: bool = False,
    plan_out: Optional[Path] = None,
    plan_fsync: bool = False,
    dedupe_root: Optional[Path] = None,
) -> int:
    if not plan_path.exists():
        raise FileNotFoundError(f"plan not found: {plan_path}")

    run_id = uuid.uuid4().hex[:12]
    writer = None
    if plan_out is not None:
        plan_out.parent.mkdir(parents=True, exist_ok=True)
        fp = open(plan_out, "a", encoding="utf-8", newline="\n")
        writer = PlanWriter(fp, run_id, fsync=plan_fsync)
        writer.run_start({
            "mode": "replay",
            "plan_in": str(plan_path),
            "on_conflict": on_conflict,
            "dedupe": dedupe,
            "dry_run": dry_run,
            "dedupe_root": str(dedupe_root) if dedupe_root else None,
        })
        logger.info("replay plan_out -> %s", plan_out)

    idx: Dict[Sig, Path] = {}
    if dedupe and dedupe_root is not None:
        logger.info("replay: building dedupe index under %s ...", dedupe_root)
        idx = build_dedupe_index(dedupe_root, logger)

    scanned = done = skipped = failed = 0

    try:
        for ev in read_json(plan_path):
            op = str(ev.get("op", ""))
            status = str(ev.get("status", ""))

            if op not in ("COPY", "MOVE") or status != "DRY":
                continue

            scanned += 1
            src_s = ev.get("src")
            dst_s = ev.get("dst")
            if not src_s or not dst_s:
                skipped += 1
                continue

            src = Path(src_s)
            dst_base = Path(dst_s)

            try:
                if not src.exists():
                    raise FileNotFoundError(f"src missing: {src}")

                sig = None
                sha256 = None
                if dedupe:
                    sig = _sig_for(src)
                    sha256 = sig[1]
                    if sig in idx:
                        skipped += 1
                        if writer:
                            writer.item({
                                "op": "SKIP",
                                "status": "SKIPPED",
                                "src": str(src),
                                "dst": str(dst_base),
                                "reason": "dedupe_duplicate_of",
                                "sha256": sha256,
                                "duplicate_of": str(idx[sig]),
                                "dry_run": dry_run,
                                "from_plan": str(plan_path),
                            })
                        continue

                dst_final, conflict_decision = resolve_dst(dst_base, on_conflict)
                if conflict_decision == "skip":
                    skipped += 1
                    if writer:
                        writer.item({
                            "op": "SKIP",
                            "status": "SKIPPED",
                            "src": str(src),
                            "dst": str(dst_base),
                            "dst_final": str(dst_final),
                            "reason": "conflict_skip",
                            "on_conflict": on_conflict,
                            "dry_run": dry_run,
                            "from_plan": str(plan_path),
                        })
                    continue

                if dry_run:
                    if writer:
                        writer.item({
                            "op": op,
                            "status": "DRY",
                            "src": str(src),
                            "dst": str(dst_final),
                            "dst_base": str(dst_base),
                            "conflict": conflict_decision,
                            "on_conflict": on_conflict,
                            "sha256": sha256,
                            "dry_run": True,
                            "from_plan": str(plan_path),
                        })
                    if dedupe and sig is not None:
                        idx[sig] = dst_final
                    continue

                dst_final.parent.mkdir(parents=True, exist_ok=True)
                if conflict_decision == "overwrite":
                    remove_if_exists(dst_final)

                if op == "COPY":
                    do_copy(src, dst_final)
                else:
                    do_move(src, dst_final)

                done += 1
                if writer:
                    writer.item({
                        "op": op,
                        "status": "OK",
                        "src": str(src),
                        "dst": str(dst_final),
                        "dst_base": str(dst_base),
                        "conflict": conflict_decision,
                        "on_conflict": on_conflict,
                        "sha256": sha256,
                        "dry_run": False,
                        "from_plan": str(plan_path),
                    })
                if dedupe and sig is not None:
                    idx[sig] = dst_final

            except Exception as e:
                failed += 1
                logger.error("[REPLAY FAIL] %s -> %s (%s)", src_s, dst_s, e)
                if writer:
                    writer.item({
                        "op": "FAIL",
                        "status": "ERROR",
                        "wanted_op": op,
                        "src": src_s,
                        "dst": dst_s,
                        "error": f"{type(e).__name__}: {e}",
                        "from_plan": str(plan_path),
                    })

    finally:
        summary = {"items": scanned, "done": done, "skipped": skipped, "failed": failed}
        logger.info("replay summary: %s", summary)
        if writer:
            writer.run_end(summary)
            writer.fp.close()

    return 0 if failed == 0 else 2


def run_undo(
    plan_path: Path,
    logger: logging.Logger,
    *,
    on_conflict: str = "rename",
    dry_run: bool = False,
    trash_dir: Optional[Path] = None,
    plan_out: Optional[Path] = None,
    plan_fsync: bool = False,
) -> int:
    if not plan_path.exists():
        raise FileNotFoundError(f"plan not found: {plan_path}")

    run_id = uuid.uuid4().hex[:12]
    writer = None
    if plan_out is not None:
        plan_out.parent.mkdir(parents=True, exist_ok=True)
        fp = open(plan_out, "a", encoding="utf-8", newline="\n")
        writer = PlanWriter(fp, run_id, fsync=plan_fsync)
        writer.run_start({
            "mode": "undo",
            "plan_in": str(plan_path),
            "on_conflict": on_conflict,
            "dry_run": dry_run,
            "trash_dir": str(trash_dir) if trash_dir else None,
        })
        logger.info("undo plan_out -> %s", plan_out)

    if trash_dir is None:
        trash_dir = plan_path.parent / ".undo_trash"

    ensured_trash = False

    scanned = undone = skipped = failed = 0

    try:
        for ev in read_json(plan_path):
            op = str(ev.get("op", ""))
            status = str(ev.get("status", ""))

            if op not in ("COPY", "MOVE") or status != "OK":
                continue

            scanned += 1
            src_s = ev.get("src")
            dst_s = ev.get("dst")
            if not src_s or not dst_s:
                skipped += 1
                continue

            src = Path(src_s)
            dst = Path(dst_s)

            try:
                if op == "MOVE":
                    if not dst.exists():
                        skipped += 1
                        if writer:
                            writer.item({
                                "op": "UNDO_MOVE",
                                "status": "SKIPPED",
                                "src": str(src),
                                "dst": str(dst),
                                "reason": "dst_missing",
                                "dry_run": dry_run,
                                "from_plan": str(plan_path),
                            })
                        continue

                    src_final, decision = resolve_dst(src, on_conflict)
                    if decision == "skip":
                        skipped += 1
                        if writer:
                            writer.item({
                                "op": "UNDO_MOVE",
                                "status": "SKIPPED",
                                "src": str(src),
                                "src_final": str(src_final),
                                "dst": str(dst),
                                "reason": "conflict_skip",
                                "on_conflict": on_conflict,
                                "dry_run": dry_run,
                                "from_plan": str(plan_path),
                            })
                        continue

                    if dry_run:
                        if writer:
                            writer.item({
                                "op": "UNDO_MOVE",
                                "status": "DRY",
                                "src": str(src),
                                "src_final": str(src_final),
                                "dst": str(dst),
                                "conflict": decision,
                                "on_conflict": on_conflict,
                                "dry_run": True,
                                "from_plan": str(plan_path),
                            })
                        continue

                    src_final.parent.mkdir(parents=True, exist_ok=True)
                    if decision == "overwrite":
                        remove_if_exists(src_final)
                    do_move(dst, src_final)

                    undone += 1
                    if writer:
                        writer.item({
                            "op": "UNDO_MOVE",
                            "status": "OK",
                            "src": str(src),
                            "src_final": str(src_final),
                            "dst": str(dst),
                            "conflict": decision,
                            "on_conflict": on_conflict,
                            "dry_run": False,
                            "from_plan": str(plan_path),
                        })

                else:  # COPY
                    if not dst.exists():
                        skipped += 1
                        if writer:
                            writer.item({
                                "op": "UNDO_COPY",
                                "status": "SKIPPED",
                                "src": str(src),
                                "dst": str(dst),
                                "reason": "dst_missing",
                                "dry_run": dry_run,
                                "from_plan": str(plan_path),
                            })
                        continue

                    if not ensured_trash and not dry_run:
                        trash_dir.mkdir(parents=True, exist_ok=True)
                        ensured_trash = True

                    trash_path = trash_dir / dst.name
                    # avoid overwrite in trash
                    trash_final, _ = resolve_dst(trash_path, "rename")

                    if dry_run:
                        if writer:
                            writer.item({
                                "op": "UNDO_COPY",
                                "status": "DRY",
                                "src": str(src),
                                "dst": str(dst),
                                "trash": str(trash_final),
                                "dry_run": True,
                                "from_plan": str(plan_path),
                            })
                        continue

                    do_move(dst, trash_final)

                    undone += 1
                    if writer:
                        writer.item({
                            "op": "UNDO_COPY",
                            "status": "OK",
                            "src": str(src),
                            "dst": str(dst),
                            "trash": str(trash_final),
                            "dry_run": False,
                            "from_plan": str(plan_path),
                        })

            except Exception as e:
                failed += 1
                logger.error("[UNDO FAIL] %s %s (%s)", op, dst_s, e)
                if writer:
                    writer.item({
                        "op": "UNDO_FAIL",
                        "status": "ERROR",
                        "undo_for": op,
                        "src": src_s,
                        "dst": dst_s,
                        "error": f"{type(e).__name__}: {e}",
                        "from_plan": str(plan_path),
                    })

    finally:
        summary = {"items": scanned, "undone": undone, "skipped": skipped, "failed": failed}
        logger.info("undo summary: %s", summary)
        if writer:
            writer.run_end(summary)
            writer.fp.close()

    return 0 if failed == 0 else 2
