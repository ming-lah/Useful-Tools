## **命令行操作与文件系统**

### 1. 命令行参数

- add_argument("--src", required=True)：必填参数
- add_argument("--dry-run", action="store_true")：布尔开关
- add_argument("--mode", choices=["ext","date"], default="ext")：限制取值
- type=int：把输入转整数（比如 --min_size_kb 10）

### 2. Pathlib路径操作


- Path(args.src).resolve()：标准化路径（绝对路径）

- src.iterdir()：遍历一级文件

- p.is_file()：只处理文件

- dst / name：路径拼接，注意不能用+

- mkdir(parents=True, exist_ok=True)：自动创建目录

- p.name / p.stem / p.suffix / p.parent：文件名与扩展名拆分

### 3. 文件元信息获取

- st = p.stat()
- st.st_size：文件大小（bytes）
- st.st_mtime：修改时间戳 → datetime.fromtimestamp → strftime("%Y-%m")

### 4.文件操作

- shutil.move(src, dst)：移动（跨盘更稳）

- shutil.copy2(src, dst)：复制并保留metadata

### 5.处理操作

- `strip()`去除两边的空格，指定字符的`strip(".")`去除两边的`.`

- `lstrip()`只去除左边的空格

- `split(sep)`按分隔符将字符串切成多段，一般需要配合`strip`去除空格使用

### 6.遍历操作

- `items = src.rglob("*")`递归遍历会搜索文件夹目录下的内容
- `items = src.iterdir()`只遍历第一层结果

---

## 运行命令汇总（tool.py）

### 1) 查看帮助/参数

- `python 01_files_automation\tool.py -h`

### 2) 常用命令（PowerShell）

- 按扩展名分类（默认 `--mode ext` + `--action copy`）：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted"`
- 只预览不执行（推荐先跑一遍确认）：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --dry-run`
- 按修改时间（年-月）分类：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --mode date`
- 递归扫描子目录：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --recursive`
- 移动而不是复制：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --action move`
- 限制最小文件大小（KB）：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --min_size_kb 100`
- 扩展名过滤（逗号分隔，`jpg,png` 或 `.jpg,.png` 都可以）：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --only-ext jpg,png`  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --exclude-ext tmp,log`

### 3) 组合示例

- 递归 + 只复制图片 + 排除 `tmp` + 最小 100KB：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --recursive --only-ext jpg,png --exclude-ext tmp --min_size_kb 100`

### 4) 注意事项

- `--dst` 不能等于 `--src`，也不能在 `--src` 目录下面（脚本会直接抛错）。
- 目标目录会按 `ext` 或 `YYYY-MM` 自动创建子文件夹；同名文件会自动追加 `_1/_2...`。
