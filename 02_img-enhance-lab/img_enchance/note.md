# Image Enhance Lab Notes

## What it does
- Command-line image enhancement tool with single-file or batch processing.
- Supported operations: linear (brightness/contrast), gamma correction, CLAHE, median denoise, unsharp mask, sobel edges.
- Handles path names with non-ASCII characters for read/write.
- Conflict handling: skip, overwrite, or auto-rename (append _1, _2, ...).

## How to run
From the project root:
```bash
python -m img_enchance <command> --src <path> --out <path> [options]
```

When `--src` is a file, `--out` can be a file path or an existing folder.
When `--src` is a folder, `--out` must be a folder path (no file suffix).

## Common options
- `--src` input image file or folder (required)
- `--out` output file (single image) or folder (batch) (required)
- `--recursive` scan folders recursively
- `--dry-run` print actions only, write nothing
- `--ext` force output extension, e.g. `.png` or `png`
- `--on-conflict` `skip|overwrite|rename` (default: `rename`)
- `--strict` stop on first error in batch mode

## Commands

### linear
Brightness/contrast: `out = alpha * img + beta`
Options:
- `--alpha` contrast multiplier (default: `1.0`)
- `--beta` brightness shift (default: `0.0`)

### gamma
Gamma correction:
- `--gamma` gamma value > 0 (default: `1.0`)

### clahe
CLAHE on LAB L channel:
- `--clip-limit` contrast limit (default: `2.0`)
- `--tile` tile grid size (default: `8`)

### median
Median filter (salt-and-pepper noise):
- `--k` odd kernel size >= 3 (default: `3`)

### unsharp
Unsharp mask:
- `--sigma` Gaussian sigma > 0 (default: `1.2`)
- `--amount` sharpen strength (default: `1.0`)

### sobel
Sobel edge magnitude (grayscale output):
- `--ksize` odd kernel size >= 1 (default: `3`)
- `--no-normalize` keep raw magnitude without normalization
If `--ext` is not provided, output defaults to `.png`.

## Examples
```bash
# Single file, linear adjust
python -m img_enchance linear --src input.jpg --out out.jpg --alpha 1.2 --beta 10

# Batch gamma correction, recursive, keep extension
python -m img_enchance gamma --src images --out out_dir --recursive --gamma 0.8

# Sobel edges to png
python -m img_enchance sobel --src input.jpg --out out_dir --ext png
```
