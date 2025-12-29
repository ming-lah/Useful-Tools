from __future__ import annotations
from pathlib import Path
from datetime import datetime
from os import stat_result

def bucket_for(file: Path, st: stat_result, mode: str) -> str:
    if mode == "ext":
        suf = file.suffix.lower().lstrip(".")
        if suf == "":
            return "no_ext"
        else:
            return suf
    if mode == "date":
        dt = datetime.fromtimestamp(st.st_mtime)
        return dt.strftime("%Y-%m")
    return "others"
