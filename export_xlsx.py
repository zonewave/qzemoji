"""Compatibility entry point for the XLSX emoji catalog exporter.

XLSX 表情图册导出器的兼容启动入口。
"""

from src.export_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
