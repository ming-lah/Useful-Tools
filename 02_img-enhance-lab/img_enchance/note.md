# Image Enhance Lab 说明

## 功能概览
- 一个支持单图/批量的图像处理 CLI。
- 支持操作：`linear`(亮度/对比度)、`gamma`(伽马)、`clahe`、`median`、`unsharp`、`sobel`、`clean-v2`(背景估计+除法校正+Otsu 二值化)。
- 读写支持包含中文/非 ASCII 路径。
- 冲突策略：`skip` / `overwrite` / `rename`（自动追加 `_1/_2/...`）。

## 运行方式
在仓库根目录执行：
```bash
cd 02_img-enhance-lab
python -m img_enchance <command> --src <path> --out <path> [options]
```

`--src` 为文件时：`--out` 可以是文件路径，或一个已存在的输出目录。
`--src` 为目录时：`--out` 必须是目录路径（不能带文件后缀）。

## 通用参数
- `--src` 输入图片文件/目录（必填）
- `--out` 输出文件（单图）/输出目录（批量）（必填）
- `--recursive` 递归扫描子目录
- `--dry-run` 只打印计划动作，不写文件
- `--ext` 强制输出扩展名，例如 `.png`/`png`
- `--on-conflict` `skip|overwrite|rename`（默认：`rename`）
- `--strict` 批处理遇到错误立即停止

## 子命令与参数

### linear
亮度/对比度：`out = alpha * img + beta`
- `--alpha` 对比度倍率（默认：`1.0`）
- `--beta` 亮度偏移（默认：`0.0`）

### gamma
伽马校正：
- `--gamma` `> 0`（默认：`1.0`）

### clahe
对 LAB 的 L 通道做 CLAHE：
- `--clip-limit`（默认：`2.0`）
- `--tile`（默认：`8`）

### median
中值滤波（椒盐噪声常用）：
- `--k` 奇数且 `>= 3`（默认：`3`）

### unsharp
USM 锐化：
- `--sigma` 高斯 sigma，`> 0`（默认：`1.2`）
- `--amount` 锐化强度（默认：`1.0`）

### sobel
Sobel 边缘幅值（灰度输出）：
- `--ksize` 奇数且 `>= 1`（默认：`3`）
- `--no-normalize` 不做归一化
不指定 `--ext` 时默认输出 `.png`。

### clean-v2（接入你提供的方法 2）
流程：灰度 -> 形态学闭运算估计背景 -> `gray / background * 255` -> Otsu 二值化。
- `--kernel` 背景估计核大小（默认：`40`，一般 `30~50`，字越大核越大）
- `--eps` 防止除 0（默认：`1e-5`）
- `--debug-bg` 保存估计背景图到指定路径（建议单图模式使用，批量会被覆盖并自动忽略）
不指定 `--ext` 时默认输出 `.png`（避免二值图写 jpg 出现压缩伪影）。

## 示例
```bash
# 单图：背景校正 + Otsu 二值化（并保存背景估计图）
python -m img_enchance clean-v2 --src D:\Desktop\1.jpg --out D:\Desktop\13.png --debug-bg D:\Desktop\debug_background.jpg

# 批量：对文件夹所有图片执行 clean-v2
python -m img_enchance clean-v2 --src D:\imgs --out D:\out --recursive --kernel 45

# 单图：Sobel 输出 png
python -m img_enchance sobel --src input.jpg --out out_dir
```
