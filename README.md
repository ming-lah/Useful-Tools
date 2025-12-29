## Useful-Tools

some useful-tools for ordering the computer, moving files

## Run

- Show help: `python 01_files_automation\tool.py -h`
- Example (dry-run): `python 01_files_automation\tool.py --src "D:\Downloads" --dst "D:\Sorted" --dry-run`

## Modules Description

### 01_files_automation/logger_utils.py

用于快速配置 Python `logging` 的实用工具模块。

- **功能**: 同时设置控制台（简洁格式）和文件（详细格式）的日志输出。
- **函数**: `setup_logging(log_file_path: Path, console_level=logging.INFO, file_level=logging.DEBUG)`
- **特点**: 自动清理旧的 Handlers，防止日志重复；文件日志使用 UTF-8 编码。
