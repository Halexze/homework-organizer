"""需求3：归档与报告 + 撤销"""

import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from .history import pop_last_operation, record_operation
from .renamer import pattern_to_regex

# 默认扩展名 → 类别映射
DEFAULT_CATEGORY_MAP = {
    ".pdf": "PDF",
    ".doc": "Word",
    ".docx": "Word",
    ".xls": "Excel",
    ".xlsx": "Excel",
    ".ppt": "PowerPoint",
    ".pptx": "PowerPoint",
    ".txt": "Text",
    ".md": "Text",
    ".zip": "Archives",
    ".rar": "Archives",
    ".7z": "Archives",
    ".jpg": "Images",
    ".jpeg": "Images",
    ".png": "Images",
    ".gif": "Images",
}


def get_category_by_ext(file_path: Path) -> str:
    """根据扩展名获取类别名"""
    ext = file_path.suffix.lower()
    return DEFAULT_CATEGORY_MAP.get(ext, "Other")


def get_category_by_name(file_path: Path, pattern: str, field: str, delimiter: str = "_") -> str | None:
    """
    根据文件名中的字段值作为类别（例如学期）。

    Args:
        file_path: 文件路径
        pattern: 文件名模式，如 {semester}_{id}_{name}_{title}
        field: 作为类别的字段名，如 semester
        delimiter: 分隔符

    Returns:
        类别名，如果无法匹配则返回 None
    """
    try:
        regex = pattern_to_regex(pattern, delimiter)
    except (ValueError, re.error):
        return None
    stem = file_path.stem
    match = regex.match(stem)
    if not match:
        return None
    fields = match.groupdict()
    return fields.get(field)


def plan_archive(
    folder: str,
    by: str = "ext",
    pattern: str | None = None,
    field: str | None = None,
    ext_filter: str | None = None,
    delimiter: str = "_",
) -> tuple[list[dict], list[dict]]:
    """
    规划归档操作。

    Returns:
        (moves, skipped)
        moves: 每项 {src, dst, category}
        skipped: 每项 {path, reason}
    """
    folder_path = Path(folder)
    moves = []
    skipped = []

    # 扩展名过滤
    exts = None
    if ext_filter:
        exts = {e.strip().lower() for e in ext_filter.split(",") if e.strip()}
        exts = {e if e.startswith(".") else f".{e}" for e in exts}

    for entry in sorted(folder_path.iterdir()):
        if not entry.is_file():
            continue
        # 跳过历史文件
        if entry.name == ".organizer_history.json":
            continue
        if exts and entry.suffix.lower() not in exts:
            continue

        # 确定类别
        if by == "ext":
            category = get_category_by_ext(entry)
        elif by == "name":
            if not pattern or not field:
                skipped.append(
                    {"path": str(entry), "reason": "by=name 需要指定 --pattern 和 --field"}
                )
                continue
            category = get_category_by_name(entry, pattern, field, delimiter)
            if category is None:
                skipped.append(
                    {"path": str(entry), "reason": f"文件名不匹配模式 '{pattern}'"}
                )
                continue
        else:
            skipped.append({"path": str(entry), "reason": f"未知归档方式: {by}"})
            continue

        dst_dir = folder_path / category
        dst = dst_dir / entry.name

        # 如果源和目标相同（已在该子文件夹中），跳过
        if entry.resolve() == dst.resolve():
            skipped.append({"path": str(entry), "reason": "文件已在对应类别文件夹中"})
            continue

        # 检查目标是否已存在
        if dst.exists():
            skipped.append(
                {"path": str(entry), "reason": f"目标位置已存在同名文件: {category}/{entry.name}"}
            )
            continue

        moves.append({"src": str(entry), "dst": str(dst), "category": category})

    return moves, skipped


def execute_archive(moves: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    执行归档移动操作。

    Returns:
        (done, failed)
    """
    done = []
    failed = []
    for move in moves:
        src = Path(move["src"])
        dst = Path(move["dst"])
        # 二次检查
        if not src.exists():
            failed.append({**move, "reason": "源文件不存在"})
            continue
        if dst.exists():
            failed.append({**move, "reason": "目标文件已存在"})
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            done.append(move)
        except OSError as e:
            failed.append({**move, "reason": str(e)})
    return done, failed


def generate_report(folder: str, moves: list[dict], skipped: list[dict], failed: list[dict]) -> str:
    """生成整理报告文本"""
    lines = []
    lines.append("=" * 60)
    lines.append("作业整理报告")
    lines.append("=" * 60)
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"目标文件夹: {folder}")
    lines.append("")
    lines.append(f"成功归档: {len(moves)} 个文件")
    lines.append(f"跳过: {len(skipped)} 个文件")
    lines.append(f"失败: {len(failed)} 个文件")
    lines.append("")

    if moves:
        lines.append("-" * 40)
        lines.append("【已归档文件】")
        for m in moves:
            lines.append(f"  {Path(m['src']).name}  →  {m['category']}/")
        lines.append("")

    if skipped:
        lines.append("-" * 40)
        lines.append("【跳过的文件及原因】")
        for s in skipped:
            lines.append(f"  - {Path(s['path']).name}: {s['reason']}")
        lines.append("")

    if failed:
        lines.append("-" * 40)
        lines.append("【失败的文件及原因】")
        for f in failed:
            lines.append(f"  ✗ {Path(f['src']).name}: {f['reason']}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)


def cmd_archive(args) -> int:
    """archive 子命令处理函数"""
    folder = args.folder
    folder_path = Path(folder)
    if not folder_path.exists():
        print(f"错误: 文件夹不存在: {folder}")
        return 1

    by = getattr(args, "by", "ext")
    pattern = getattr(args, "pattern", None)
    field = getattr(args, "field", None)
    delimiter = getattr(args, "delimiter", "_")

    moves, skipped = plan_archive(folder, by, pattern, field, args.ext, delimiter)

    # 打印预览
    print("=" * 60)
    print("归档计划预览（尚未执行）")
    print("=" * 60)
    if moves:
        for m in moves:
            print(f"  {Path(m['src']).name}  →  {m['category']}/")
    else:
        print("  （没有可归档的文件）")

    if skipped:
        print("-" * 60)
        print(f"跳过 {len(skipped)} 个文件:")
        for s in skipped:
            print(f"  - {Path(s['path']).name}: {s['reason']}")

    print("=" * 60)
    print(f"将归档 {len(moves)} 个文件，跳过 {len(skipped)} 个。")

    if not moves:
        print("没有需要执行的操作。")
        return 0

    # 确认
    try:
        answer = input("确认执行以上归档？(y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        return 1

    if answer not in ("y", "yes"):
        print("已取消，未做任何修改。")
        return 0

    done, failed = execute_archive(moves)

    # 记录历史（仅记录成功的移动，用于撤销）
    if done:
        record_operation(
            folder,
            {
                "type": "archive",
                "moves": [{"from": m["src"], "to": m["dst"]} for m in done],
            },
        )

    # 生成并打印报告
    report = generate_report(folder, done, skipped, failed)
    print()
    print(report)

    # 保存报告到文件
    report_path = folder_path / f"整理报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"报告已保存至: {report_path}")
    except OSError as e:
        print(f"警告: 无法保存报告文件: {e}")

    return 0 if not failed else 1


def cmd_undo(args) -> int:
    """undo 子命令处理函数"""
    folder = args.folder
    folder_path = Path(folder)
    if not folder_path.exists():
        print(f"错误: 文件夹不存在: {folder}")
        return 1

    last_op = pop_last_operation(folder)
    if last_op is None:
        print("没有可撤销的操作。")
        return 0

    op_type = last_op.get("type", "unknown")
    moves = last_op.get("moves", [])
    timestamp = last_op.get("timestamp", "unknown")

    print("=" * 60)
    print(f"撤销上次操作（{op_type} @ {timestamp}）")
    print("=" * 60)

    if not moves:
        print("该操作没有可撤销的移动。")
        return 0

    # 反向移动
    restored = 0
    failed = []
    for move in moves:
        src = Path(move["to"])  # 当前位置
        dst = Path(move["from"])  # 原始位置
        if not src.exists():
            failed.append({"file": str(src), "reason": "文件不存在（可能已被手动移动/删除）"})
            continue
        if dst.exists():
            failed.append({"file": str(src), "reason": f"原始位置已有文件: {dst}"})
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            restored += 1
            print(f"  ↺ {src.name} 恢复到原位置")
        except OSError as e:
            failed.append({"file": str(src), "reason": str(e)})

    print("-" * 60)
    print(f"撤销完成：恢复 {restored} 个文件，失败 {len(failed)} 个。")
    if failed:
        for f in failed:
            print(f"  ✗ {Path(f['file']).name}: {f['reason']}")

    # 清理空的类别文件夹
    for move in moves:
        subfolder = Path(move["to"]).parent
        if subfolder.exists() and subfolder.is_dir():
            try:
                # 仅删除空文件夹
                if not any(subfolder.iterdir()):
                    subfolder.rmdir()
            except OSError:
                pass

    return 0 if not failed else 1

