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