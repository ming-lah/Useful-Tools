from pathlib import Path

def next_available(p: Path) -> Path:
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
    
def resolve_conflict(dst: Path, on_conflict: str) -> Path | None:
    if not dst.exists():
        return dst
    if on_conflict=="overwrite":
        return dst
    if on_conflict=="skip":
        return None
    if on_conflict=="rename":
        return next_available(dst)
    raise ValueError(f"Unknown on_conflict: {on_conflict}")
