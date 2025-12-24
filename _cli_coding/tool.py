import argparse
import shutil
from pathlib import Path
from datetime import datetime

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
def get_name(f:Path, mode: str) -> str:
    st = f.stat()
    if mode == "ext":
        suf = f.suffix.lower().lstrip(".")
        if suf == "":
            suf = "no_ext"
        return suf
    else:
        ts = st.st_mtime
        dt = datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m")

def sort_files(src: Path, dst: Path, mode: str, dry: bool, min_size: int, action: str) -> None:
    moved = 0
    scanned = 0
    skipped = 0
    for f in src.iterdir():
        if not f.is_file():
            continue
        scanned += 1
        st = f.stat()
        size = st.st_size
        size = size / 1024

        # skip small size
        if size < min_size:
            skipped += 1
            print(f"[Skipped] {f.name} size={size:.4f}KB")
            continue
        name = get_name(f, mode)

        target_dir = dst / name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = next_available(target_dir/f.name)

        if dry:
            print(f"[DRY] {f} -> {target_path}")
        else:
            if action == "copy":
                shutil.copy2(str(f), str(target_path))
                print(f"[COPY] {f} -> {target_path}")
            else:
                shutil.move(str(f), str(target_path))
                print(f"[MOVE] {f} -> {target_path}")
            moved += 1
            
    print(f"\nDone. mode={mode} dry={dry} min_size_kb={min_size}kb")
    print(f"Done. scanned{scanned} moved{moved} skipped{skipped}")





def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--mode", choices=["ext", "date"], default="ext")
    ap.add_argument("--min_size_kb", type=int, default=0)
    ap.add_argument("--action", choices=["copy", "move"], default="copy")
    args = ap.parse_args()

    src = Path(args.src).expanduser().resolve()
    dst = Path(args.dst).expanduser().resolve()
    dst.mkdir(parents=True, exist_ok=True)

    action  = args.action
    sort_files(src, dst, args.mode, args.dry_run, args.min_size_kb, action)

if __name__ == "__main__":
    main()


