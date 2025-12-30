from pathlib import Path
from typing import Iterator
import cv2
import numpy as np

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

def is_image(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in IMG_EXTS

def iter_images(src: Path, recursive: bool) -> Iterator[Path]:
    if src.is_file():
        if is_image(src):
            yield src
        return
    
    if recursive:
        it = src.rglob("*")
    else:
        it = src.glob("*")
    for p in it:
        if is_image(p):
            yield p


def ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def read_bgr(path: Path) -> np.ndarray:
    """
    Read image with non-ASCII path support.
    """
    try:
        raw_data = np.fromfile(str(path), dtype=np.uint8)
        img = cv2.imdecode(raw_data, cv2.IMREAD_COLOR)
    except Exception:
        img = None
    if img is None:
        raise ValueError(f"Failed to read image: {path}")
    return img

def write_img(path: Path, img: np.ndarray) -> None:
    ensure_parent(path)
    ext = path.suffix
    if not ext:
        raise ValueError(f"Output path has no extension: {path}")
    ok, buf = cv2.imencode(ext, img)
    if not ok:
        raise ValueError(f"Failed to encode image: {path}")
    try:
        buf.tofile(str(path))
    except Exception:
        raise ValueError(f"Failed to write image: {path}")
