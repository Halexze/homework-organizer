"""需求1：扫描与列出文件"""

import os
from datetime import datetime
from pathlib import Path


def human_size(size_bytes: int) -> str:
    """将字节数转换为人类可读的大小"""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024
        i += 1
    return f"{size:.1f} {units[i]}"


def scan_files(folder: str, ext_filter: str | None = None) -> list[dict]:
    """
    扫描文件夹，返回所有文件信息列表。

    Args:
        folder: 要扫描的文件夹路径
        ext_filter: 扩展名过滤，多个用逗号分隔，如 ".pdf,.docx"。为 None 表示不过滤。

    Returns:
        文件信息字典列表，每项包含 name, path, size, size_human, modified
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"文件夹不存在: {folder}")
    if not folder_path.is_dir():
        raise NotADirectoryError(f"不是文件夹: {folder}")

    # 解析扩展名过滤
    exts = None
    if ext_filter:
        exts = {e.strip().lower() for e in ext_filter.split(",") if e.strip()}
        # 确保扩展名以点开头
        exts = {e if e.startswith(".") else f".{e}" for e in exts}

    results = []
    for entry in sorted(folder_path.iterdir()):
        if not entry.is_file():
            continue
        if exts and entry.suffix.lower() not in exts:
            continue
        stat = entry.stat()
        results.append(
            {
                "name": entry.name,
                "path": str(entry),
                "size": stat.st_size,
                "size_human": human_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "ext": entry.suffix.lower(),
            }
        )
    return results


def cmd_list(args) -> int:
    """list 子命令处理函数"""
    try:
        files = scan_files(args.folder, args.ext)
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"错误: {e}")
        return 1

    if not files:
        print("未找到任何文件。")
        if args.ext:
            print(f"（已按扩展名过滤: {args.ext}）")
        return 0

    # 打印表头
    print(f"{'文件名':<40} {'大小':>10} {'修改时间':<20}")
    print("-" * 72)
    for f in files:
        # 文件名过长时截断
        name = f["name"]
        if len(name) > 38:
            name = name[:35] + "..."
        print(f"{name:<40} {f['size_human']:>10} {f['modified']:<20}")

    print("-" * 72)
    print(f"共 {len(files)} 个文件")
    return 0
