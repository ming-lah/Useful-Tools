from __future__ import annotations
import shutil
from pathlib import Path

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

def do_copy(src: Path, dst: Path) -> None:
    shutil.copy2(str(src), str(dst))

def do_move(src: Path, dst: Path) -> None:
    shutil.move(str(src), str(dst))