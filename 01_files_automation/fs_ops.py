from __future__ import annotations
import shutil
from pathlib import Path
from typing import Tuple

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def next_available(p:Path) -> Path:
    if not p.exists():
        return p
    stem = p.stem
    suf = p.suffix
    parent = p.parent

    i = 1
    while True:
        cand = parent / f"{stem}_{i}{suf}"
        if not cand.exists():
            return cand
        i += 1

def resolve_dst(dst: Path, on_conflict: str) -> Tuple[Path, str]:
    if not dst.exists():
        return dst, "none"
    if on_conflict == "rename":
        return next_available(dst), "rename"
    if on_conflict == "skip":
        return dst, "skip"
    if on_conflict == "overwrite":
        return dst, "overwrite"
    if on_conflict == "fail":
        raise FileExistsError(f"conflict: {dst}")
    raise ValueError(f"unknown on_conflict: {on_conflict}")

def resolve_conflict(dst: Path, on_conflict: str) -> Tuple[Path, str]:
    # Backward-compatible alias
    return resolve_dst(dst, on_conflict)

def remove_if_exists(p: Path) -> None:
    try:
        if p.exists():
            p.unlink()
    except IsADirectoryError:
        raise

def do_copy(src: Path, dst: Path) -> None:
    shutil.copy2(str(src), str(dst))

def do_move(src: Path, dst: Path) -> None:
    shutil.move(str(src), str(dst))
