"""需求2：批量改名"""

import re
import sys
from pathlib import Path


def pattern_to_regex(pattern: str, delimiter: str = "_") -> re.Pattern:
    """
    将命名模式转换为正则表达式。

    模式示例："{id}_{name}_{title}"
    - 最后一个字段允许包含分隔符（贪婪匹配）
    - 其他字段不允许包含分隔符

    Args:
        pattern: 包含 {字段名} 占位符的模式
        delimiter: 字段分隔符，默认下划线

    Returns:
        编译后的正则表达式
    """
    # 提取所有 {字段名}
    fields = re.findall(r"\{(\w+)\}", pattern)
    if not fields:
        raise ValueError(f"模式中未找到字段占位符: {pattern}")

    # 将模式转换为正则
    # 先把 {field} 替换为占位标记，再构造正则
    regex_parts = []
    for i, field in enumerate(fields):
        # 转义分隔符
        delim = re.escape(delimiter)
        if i == len(fields) - 1:
            # 最后一个字段：贪婪匹配，允许包含分隔符
            regex_parts.append(f"(?P<{field}>.+)")
        else:
            # 非最后字段：不允许包含分隔符
            regex_parts.append(f"(?P<{field}>[^{delim}]+)")

    # 用分隔符连接各字段的正则
    # 需要从原模式中提取分隔符序列
    # 简单做法：按 {field} 分割模式，取中间的分隔符部分
    segments = re.split(r"\{\w+\}", pattern)
    # segments 示例: ['', '_', '_', '']
    # 我们需要字段之间的分隔符：segments[1], segments[2], ...
    # 构造完整正则
    pattern_regex = "^"
    for i, part in enumerate(regex_parts):
        if i > 0 and i < len(segments):
            # 字段之间的分隔符
            sep = segments[i]
            pattern_regex += re.escape(sep)
        pattern_regex += part
    pattern_regex += "$"
    return re.compile(pattern_regex)


def build_new_name(stem: str, pattern_regex: re.Pattern, output_template: str) -> str | None:
    """
    根据输入模式和输出模板生成新文件名（不含扩展名）。

    Args:
        stem: 原文件名（不含扩展名）
        pattern_regex: 编译后的输入模式正则
        output_template: 输出模板，如 "{title}_{id}"

    Returns:
        新文件名（不含扩展名），如果不匹配则返回 None
    """
    match = pattern_regex.match(stem)
    if not match:
        return None
    fields = match.groupdict()
    try:
        return output_template.format(**fields)
    except (KeyError, IndexError):
        return None


def plan_renames(
    folder: str,
    pattern: str,
    output_template: str,
    ext_filter: str | None = None,
    delimiter: str = "_",
) -> tuple[list[dict], list[dict]]:
    """
    规划重命名操作。

    Returns:
        (rename_plan, skipped)
        rename_plan: 每项 {old_path, new_path, old_name, new_name}
        skipped: 每项 {path, reason}
    """
    folder_path = Path(folder)
    pattern_regex = pattern_to_regex(pattern, delimiter)

    # 解析扩展名过滤
    exts = None
    if ext_filter:
        exts = {e.strip().lower() for e in ext_filter.split(",") if e.strip()}
        exts = {e if e.startswith(".") else f".{e}" for e in exts}

    rename_plan = []
    skipped = []

    for entry in sorted(folder_path.iterdir()):
        if not entry.is_file():
            continue
        if exts and entry.suffix.lower() not in exts:
            continue

        new_stem = build_new_name(entry.stem, pattern_regex, output_template)
        if new_stem is None:
            skipped.append(
                {"path": str(entry), "reason": f"文件名不匹配模式 '{pattern}'"}
            )
            continue

        new_name = new_stem + entry.suffix
        new_path = entry.parent / new_name

        if new_path == entry:
            skipped.append({"path": str(entry), "reason": "文件名无需修改"})
            continue

        # 检查目标是否已存在（冲突）
        if new_path.exists():
            skipped.append(
                {"path": str(entry), "reason": f"目标文件已存在，跳过: {new_name}"}
            )
            continue

        rename_plan.append(
            {
                "old_path": str(entry),
                "new_path": str(new_path),
                "old_name": entry.name,
                "new_name": new_name,
            }
        )

    return rename_plan, skipped


def cmd_rename(args) -> int:
    """rename 子命令处理函数"""
    folder = args.folder
    pattern = args.pattern
    output = args.output

    if not pattern or not output:
        print("错误: 必须提供 --pattern 和 --output 参数", file=sys.stderr)
        return 1

    folder_path = Path(folder)
    if not folder_path.exists():
        print(f"错误: 文件夹不存在: {folder}")
        return 1

    try:
        rename_plan, skipped = plan_renames(
            folder, pattern, output, args.ext, delimiter=args.delimiter
        )
    except (ValueError, re.error) as e:
        print(f"错误: {e}")
        return 1

    # 打印计划
    print("=" * 60)
    print("重命名计划预览（尚未执行）")
    print("=" * 60)
    if rename_plan:
        for item in rename_plan:
            print(f"  {item['old_name']}")
            print(f"    → {item['new_name']}")
    else:
        print("  （没有可重命名的文件）")

    if skipped:
        print("-" * 60)
        print(f"跳过 {len(skipped)} 个文件:")
        for item in skipped:
            print(f"  - {Path(item['path']).name}: {item['reason']}")

    print("=" * 60)
    print(f"将重命名 {len(rename_plan)} 个文件，跳过 {len(skipped)} 个。")

    if not rename_plan:
        print("没有需要执行的操作。")
        return 0

    # 确认
    try:
        answer = input("确认执行以上重命名？(y/N): ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        return 1

    if answer not in ("y", "yes"):
        print("已取消，未做任何修改。")
        return 0

    # 执行重命名
    success = 0
    failed = []
    for item in rename_plan:
        old_path = Path(item["old_path"])
        new_path = Path(item["new_path"])
        # 二次检查冲突（在打印到确认之间可能有变化）
        if new_path.exists():
            failed.append(
                {"old": item["old_name"], "new": item["new_name"], "reason": "目标文件已存在"}
            )
            continue
        try:
            old_path.rename(new_path)
            success += 1
            print(f"  ✓ {item['old_name']} → {item['new_name']}")
        except OSError as e:
            failed.append(
                {"old": item["old_name"], "new": item["new_name"], "reason": str(e)}
            )

    print("-" * 60)
    print(f"完成：成功 {success} 个，失败 {len(failed)} 个。")
    if failed:
        for f in failed:
            print(f"  ✗ {f['old']} → {f['new']}: {f['reason']}")
    return 0 if not failed else 1
