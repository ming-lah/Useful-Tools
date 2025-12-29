## **命令行操作与文件系统**

### 1. 命令行参数

- `--src`：源目录（必填）
- `--dst`：目标目录（必填）
- `--mode`：分组方式，`ext`（按扩展名）/ `date`（按修改时间 `YYYY-MM`）
- `--action`：文件处理方式，`copy`（默认）/ `move`
- `--recursive`：递归扫描子目录（默认只扫描第一层）
- `--min_size_kb`：最小文件大小（KB，默认 0）
- `--only-ext`：只处理这些扩展名（逗号分隔，如 `jpg,png`，可带 `.`）
- `--exclude-ext`：排除这些扩展名（逗号分隔）
- `--dry-run`：只打印将要执行的操作，不实际复制/移动
- `--log-level`：控制台日志级别（仅影响控制台输出，不影响日志文件）
- `--log-file`：指定日志文件路径；为空则默认写入 `--dst\\logs\\sort_YYYYMMDD_HHMMSS.log`

### 2. Pathlib路径操作

- Path(args.src).resolve()：标准化路径（绝对路径）
- Path(...).expanduser()：展开 `~` 这类用户目录（如果你传了）
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

## 日志（logging）与排错笔记

### 1) 日志文件在哪里、怎么开关

- 默认日志文件：如果不传 `--log-file`，脚本会在 `--dst\\logs\\` 下创建 `sort_YYYYMMDD_HHMMSS.log`
- 自定义日志文件：传 `--log-file "D:\\path\\to\\xxx.log"`，脚本会自动创建父目录
- 控制台日志：由 `--log-level` 控制（默认 `INFO`）
- 文件日志：固定写入 `DEBUG` 级别（用于事后追踪更完整信息）

### 2) 关键 API/实现点（`logger_utils.py`）

- `logging.getLogger()`：拿到 root logger，统一管理输出
- `logger.setLevel(logging.DEBUG)`：logger 总开关开到 DEBUG，让 handler 决定过滤
- `logger.handlers.clear()`：避免重复运行脚本时日志重复打印
- `logging.FileHandler(log_file_path, encoding="utf-8")`：写入文件日志（UTF-8）
- `logging.StreamHandler(sys.stdout)`：控制台输出
- `logging.Formatter(...)`：控制日志格式（文件里包含时间、级别、文件名和行号）

### 3) 脚本里都记录了什么（`tool.py`）

- 扫描开始：`scan start: src=... recursive=...`
- 每个文件：`[SKIP]` / `[DRY]` / `[COPY]` / `[MOVE]`
- 异常：`[FAIL] Permission denied` 或 `[FAIL] Error processing ...`
- 汇总：`summary: scanned=... moved=... skipped=...`

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
- 输出更详细的控制台日志（同时日志文件始终会写 DEBUG）：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --log-level DEBUG`
- 指定日志文件位置：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --log-file "D:\Sorted\logs\manual.log"`

### 3) 组合示例

- 递归 + 只复制图片 + 排除 `tmp` + 最小 100KB：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --recursive --only-ext jpg,png --exclude-ext tmp --min_size_kb 100`

### 4) 最新完整命令示例（建议先预览）

- 全量参数（预览不执行）：  
  `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --mode date --action copy --recursive --min_size_kb 100 --only-ext jpg,png --exclude-ext tmp,log --dry-run --log-level DEBUG --log-file "D:\Sorted\logs\sort_manual.log"`
- 实际执行：把上面命令里的 `--dry-run` 去掉即可

### 5) 注意事项

- `--dst` 不能等于 `--src`，也不能在 `--src` 目录下面（脚本会直接抛错）。
- 目标目录会按 `ext` 或 `YYYY-MM` 自动创建子文件夹；同名文件会自动追加 `_1/_2...`。
