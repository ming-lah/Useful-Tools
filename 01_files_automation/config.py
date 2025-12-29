from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set, Dict, Any

def parse_ext_list(s: str) -> Set[str]:
    if not s:
        return set()
    parts = s.split(",")
    out = set()
    for x in parts:
        part = x.strip().lower().lstrip(".")
        if part:
            # set->add
            out.add(part)
    return out 

@dataclass(frozen=True)
class RunConfig:
    src: Path
    dst: Path
    recursive: bool
    mode: str
    action: str
    dry_run: bool

    only_ext: Set[str]
    exclude_ext: Set[str]
    min_size_kb: int

    plan_out: Optional[Path]
    plan_fsync: bool

    log_file: Optional[Path]
    console_level: int
    file_level: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "src": str(self.src),
            "dst": str(self.dst),
            "recursive": self.recursive,
            "mode": self.mode,
            "action": self.action,
            "dry_run": self.dry_run,
            "only_ext": sorted(self.only_ext),
            "exclude_ext": sorted(self.exclude_ext),
            "min_size_kb": self.min_size_kb,
            "plan_out": str(self.plan_out) if self.plan_out else None,
            "plan_fsync": self.plan_fsync,
            "log_file": str(self.log_file) if self.log_file else None,
        }


def validate_config(cfg: RunConfig) -> None:
    if not cfg.src.exists():
        raise FileNotFoundError(f"src not found: {cfg.src}")
    if not cfg.src.is_dir():
        raise NotADirectoryError(f"src is not a directory: {cfg.src}")

    src_resolved = cfg.src.resolve(strict=False)
    dst_resolved = cfg.dst.resolve(strict=False)
    if src_resolved == dst_resolved or src_resolved in dst_resolved.parents:
        raise ValueError(f"dst must NOT be inside src. src={cfg.src} dst={cfg.dst}")

    cfg.dst.mkdir(parents=True, exist_ok=True)
