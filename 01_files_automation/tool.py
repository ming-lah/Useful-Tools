import argparse
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional , Tuple, Set
import json
import logging
from logger_utils import setup_logging

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

def get_files(src: Path, recursive: bool) -> List[Path]:
    if recursive:
        items = src.rglob("*")
    else:
        items = src.iterdir()
    files = []
    for f in items:
        if f.is_file():
            files.append(f)
    return files

def parse_ext_list(s: str) -> Set[str]:
    if not s:
        return set()
    parts = s.split(",")
    out = set()
    for x in parts:
        part = x.strip().lower().lstrip(".")
        if part:
            out.add(part)
    return out

def sort_files(
    src: Path, 
    dst: Path, 
    mode: str, 
    dry: bool, 
    min_size: int, 
    action: str, 
    recursive: bool,
    onlyset: str,
    excludeset: str,
    logger: logging.Logger
) -> None:
    moved = 0
    scanned = 0
    skipped = 0
    files = get_files(src, recursive)

    onset = parse_ext_list(onlyset)
    exset = parse_ext_list(excludeset)

    logger.info("scan start: src=%s recursive=%s",src,recursive)
    for f in files:
        try:
            scanned += 1
            st = f.stat()
            size = st.st_size
            size = size / 1024

            # skip
            if size < min_size:
                skipped += 1
                logger.info("[SKIP] %s size=%.4fKB < min=%sKB",f.name,size,min_size)
                continue
            suf = f.suffix.lower().lstrip(".")
            if suf == "":
                suf = "no_ext"
            if onset and suf not in onset:
                skipped += 1
                logger.info("[SKIP] %s ext=%s not in only_ext=%s",f.name,suf,sorted(onset))
                continue
            if exset and suf in exset:
                skipped += 1
                logger.info("[SKIP] %s ext=%s in exclude_ext=%s",f.name,suf,sorted(exset))
                continue

            name = get_name(f, mode)

            target_dir = dst / name
            target_dir.mkdir(parents=True, exist_ok=True)
            target_path = next_available(target_dir/f.name)

            if dry:
                logger.info("[DRY] %s -> %s",f,target_path)
            else:
                if action == "copy":
                    shutil.copy2(str(f), str(target_path))
                    logger.info("[COPY] %s -> %s",f,target_path)
                else:
                    shutil.move(str(f), str(target_path))
                    logger.info("[MOVE] %s -> %s",f,target_path)
                moved += 1
        except PermissionError:
            logger.error("[FAIL] Permission denied: %s", f)
            skipped += 1
        except Exception as e:
            logger.error("[FAIL] Error processing %s: %s", f, e)
            skipped += 1
            
    logger.info("done: mode=%s dry=%s min_size_kb=%s",mode,dry,min_size)
    logger.info("summary: scanned=%d moved=%d skipped=%d",scanned,moved,skipped)

def log_event(fp, ev:dict) -> None:
    fp.write(json.dumps(ev, ensure_ascii=False) + "\n")




def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--mode", choices=["ext", "date"], default="ext")
    ap.add_argument("--min_size_kb", type=int, default=0)
    ap.add_argument("--action", choices=["copy", "move"], default="copy")
    ap.add_argument("--recursive",action="store_true")
    ap.add_argument("--only-ext", default="")
    ap.add_argument("--exclude-ext",default="")

    ap.add_argument("--log-level", default='INFO', choices=["DEBUG","INFO","WARNING","ERROR","CRITICAL"])
    ap.add_argument("--log-file", default="")

    args = ap.parse_args()

    src = Path(args.src).expanduser().resolve()
    dst = Path(args.dst).expanduser().resolve()
    if src == dst or src in dst.parents:
        raise ValueError("dst can't be src or dst can't under src")
    dst.mkdir(parents=True, exist_ok=True)

    if args.log_file:
        log_file_path=Path(args.log_file).expanduser().resolve()
        log_file_path.parent.mkdir(parents=True,exist_ok=True)
    else:
        log_dir=dst/"logs"
        log_dir.mkdir(parents=True,exist_ok=True)
        ts=datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path=log_dir/f"sort_{ts}.log"

    logger = setup_logging(
        log_file_path,
        console_level=getattr(logging, args.log_level),
        file_level=logging.DEBUG
    )
    logger.info("start")
    logger.info("src=%s dst=%s mode=%s dry=%s action=%s recursive=%s min_size_kb=%s only_ext=%s exclude_ext=%s",
                src,dst,args.mode,args.dry_run,args.action,args.recursive,args.min_size_kb,args.only_ext,args.exclude_ext)
    logger.info("log_file=%s",log_file_path)

    recursive = args.recursive
    action  = args.action
    
    onset = args.only_ext
    excludeset = args.exclude_ext

    sort_files(src, dst, args.mode, args.dry_run, args.min_size_kb, action, recursive, onset, excludeset, logger)

    logger.info("finished")
if __name__ == "__main__":
    main()


