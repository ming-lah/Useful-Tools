import argparse
from pathlib import Path
from typing import Callable, Any
import sys

from .io_utils import iter_images, read_bgr, write_img,is_image
from .conflict import resolve_conflict
from . import ops as OPS

def map_dst_for_file(src_file:Path,out:Path,ext:str|None)->Path:
    if out.exists() and out.is_dir():
        dst=out/src_file.name
    else:
        dst=out
    if ext:
        if not ext.startswith("."):
            ext="."+ext
        dst=dst.with_suffix(ext)
    return dst

def map_dst_for_dir(src_file:Path,src_root:Path,out_root:Path,ext:str|None)->Path:
    rel=src_file.relative_to(src_root)
    dst=out_root/rel
    if ext:
        if not ext.startswith("."):
            ext="."+ext
        dst=dst.with_suffix(ext)
    return dst

def process_batch(
    src:Path,
    out:Path,
    op_fn:Callable[...,Any],
    op_kwargs:dict,
    recursive:bool,
    on_conflict:str,
    dry_run:bool,
    ext:str|None,
    strict:bool
)->int:
    total=0
    ok=0
    fail=0
    skip=0

    if src.is_file():
        if not is_image(src):
            print(f"[SKIP] Not an image: {src}")
            return 1
        dst=map_dst_for_file(src,out,ext)
        dst2=resolve_conflict(dst,on_conflict)
        if dst2 is None:
            print(f"[SKIP] {src} -> {dst}")
            return 0
        if dry_run:
            print(f"[DRY] {src} -> {dst2}")
            return 0
        try:
            img=read_bgr(src)
            out_img=op_fn(img,**op_kwargs)
            write_img(dst2,out_img)
            print(f"[OK ] {src} -> {dst2}")
            return 0
        except Exception as e:
            print(f"[ERR] {src}: {e}")
            return 1

    src_root=src
    out_root=out
    if out_root.suffix!="":
        raise ValueError("When src is a folder, --out must be a folder path (no file suffix).")

    for p in iter_images(src_root,recursive):
        total+=1
        dst=map_dst_for_dir(p,src_root,out_root,ext)
        dst2=resolve_conflict(dst,on_conflict)
        if dst2 is None:
            skip+=1
            print(f"[SKIP] {p} -> {dst}")
            continue
        if dry_run:
            print(f"[DRY] {p} -> {dst2}")
            continue
        try:
            img=read_bgr(p)
            out_img=op_fn(img,**op_kwargs)
            write_img(dst2,out_img)
            ok+=1
            print(f"[OK ] {p} -> {dst2}")
        except Exception as e:
            fail+=1
            print(f"[ERR] {p}: {e}")
            if strict:
                raise

    if dry_run:
        print(f"[DRY] planned={total}")
    else:
        print(f"[SUM] total={total},ok={ok},skip={skip},fail={fail}")
    return 0 if fail==0 else 1

def add_common_args(p:argparse.ArgumentParser)->None:
    p.add_argument("--src",required=True,help="input image file or folder")
    p.add_argument("--out",required=True,help="output file (for single image) or folder (for folder batch)")
    p.add_argument("--recursive",action="store_true",help="scan folders recursively")
    p.add_argument("--dry-run",action="store_true",help="print actions only, write nothing")
    p.add_argument("--ext",default=None,help="force output extension, e.g. .png/.jpg/.webp")
    p.add_argument("--on-conflict",choices=["skip","overwrite","rename"],default="rename")
    p.add_argument("--strict",action="store_true",help="stop on first error")

def main()->None:
    ap=argparse.ArgumentParser(prog="img_enhance",description="Image Enhance Lab (CLI)")
    sub=ap.add_subparsers(dest="cmd",required=True)

    p=sub.add_parser("linear",help="brightness/contrast: out=alpha*img+beta")
    add_common_args(p)
    p.add_argument("--alpha",type=float,default=1.0,help="contrast multiplier")
    p.add_argument("--beta",type=float,default=0.0,help="brightness shift")
    p.set_defaults(_op="linear")

    p=sub.add_parser("gamma",help="gamma correction")
    add_common_args(p)
    p.add_argument("--gamma",type=float,default=1.0,help="gamma>0, <1 brighter, >1 darker")
    p.set_defaults(_op="gamma")

    p=sub.add_parser("clahe",help="CLAHE on L channel in LAB")
    add_common_args(p)
    p.add_argument("--clip-limit",type=float,default=2.0)
    p.add_argument("--tile",type=int,default=8)
    p.set_defaults(_op="clahe")

    p=sub.add_parser("median",help="median filter (good for salt-and-pepper noise)")
    add_common_args(p)
    p.add_argument("--k",type=int,default=3,help="odd kernel size >=3")
    p.set_defaults(_op="median")

    p=sub.add_parser("unsharp",help="unsharp mask sharpening")
    add_common_args(p)
    p.add_argument("--sigma",type=float,default=1.2,help="gaussian sigma")
    p.add_argument("--amount",type=float,default=1.0,help="sharpen strength")
    p.set_defaults(_op="unsharp")

    p=sub.add_parser("sobel",help="sobel edge magnitude (outputs grayscale)")
    add_common_args(p)
    p.add_argument("--ksize",type=int,default=3)
    p.add_argument("--no-normalize",action="store_true")
    p.set_defaults(_op="sobel")

    args=ap.parse_args()
    src=Path(args.src)
    out=Path(args.out)
    ext=args.ext
    if ext and not ext.startswith("."):
        ext="."+ext

    op_name=getattr(args,"_op",None)
    if op_name is None:
        ap.error("No operation selected")

    if op_name=="linear":
        op_fn=OPS.linear
        op_kwargs={"alpha":args.alpha,"beta":args.beta}
    elif op_name=="gamma":
        op_fn=OPS.gamma
        op_kwargs={"gamma":args.gamma}
    elif op_name=="clahe":
        op_fn=OPS.clahe
        op_kwargs={"clip_limit":args.clip_limit,"tile":args.tile}
    elif op_name=="median":
        op_fn=OPS.median
        op_kwargs={"k":args.k}
    elif op_name=="unsharp":
        op_fn=OPS.unsharp
        op_kwargs={"sigma":args.sigma,"amount":args.amount}
    elif op_name=="sobel":
        op_fn=OPS.sobel
        op_kwargs={"ksize":args.ksize,"normalize":(not args.no_normalize)}
        # sobel 建议默认输出 png（无损 + 灰度）
        if ext is None:
            ext=".png"
    else:
        raise ValueError(f"Unknown op: {op_name}")

    try:
        code=process_batch(
            src=src,
            out=out,
            op_fn=op_fn,
            op_kwargs=op_kwargs,
            recursive=args.recursive,
            on_conflict=args.on_conflict,
            dry_run=args.dry_run,
            ext=ext,
            strict=args.strict
        )
        raise SystemExit(code)
    except Exception as e:
        print(f"[FATAL] {e}")
        raise SystemExit(2)
