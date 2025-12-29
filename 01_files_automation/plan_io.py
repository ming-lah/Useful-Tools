from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, IO

def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def _write_line(fp: IO[str], obj: Dict[str, Any], fsync: bool) -> None:
    """
    fp: open file
    fsync: true写入再执行
    """
    fp.write(json.dumps(obj, ensure_ascii=False) + "\n")
    fp.flush()
    if fsync:
        os.fsync(fp.fileno())

@dataclass
class PlanWriter:
    fp: IO[str]
    run_id: str
    fsync: bool = False

    def run_start(self, cfg: Dict[str, Any]) -> None:
        _write_line(self.fp, {
            "ts":now_iso(),
            "run_id": self.run_id,
            "op": "RUN_START",
            "status": "OK",
            "config": cfg,
        }, self.fsync)

    def item(self, ev: Dict[str, Any]) -> None:
        ev = dict(ev)
        ev.setdefault("ts", now_iso())
        ev.setdefault("run_id", self.run_id)
        _write_line(self.fp, ev, self.fsync)
    
    def run_end(self, summary: Dict[str, Any]) -> None:
        _write_line(self.fp, {
            "ts": now_iso(),
            "run_id": self.run_id,
            "op": "RUN_END",
            "status": "OK",
            "summary": summary,
        }, self.fsync)

def read_json(path: Path) -> Generator[Dict[str, Any], None, None]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)