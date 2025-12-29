from __future__ import annotations
from pathlib import Path
from typing import Iterator

def get_files(src: Path, recursive: bool) -> Iterator[Path]:
    """
    Yield files under `src`.

    Returns an iterator to avoid building a full list in memory.
    """
    if recursive:
        for p in src.rglob("*"):
            if p.is_file():
                yield p
    else:
        for p in src.iterdir():
            if p.is_file():
                yield p
