"""命令行入口"""

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="homework-organizer",
        description="作业文件整理工具：扫描、批量改名、归档与撤销",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list - 需求1：扫描与列出（在 feature/req1 中实现）
    p_list = subparsers.add_parser("list", help="扫描文件夹并列出文件")
    p_list.add_argument("folder", help="要扫描的文件夹路径")
    p_list.add_argument(
        "--ext",
        default=None,
        help="按扩展名过滤，多个用逗号分隔，例如：.pdf,.docx",
    )

    # rename - 需求2：批量改名（在 feature/req2 中实现）
    p_rename = subparsers.add_parser("rename", help="按规则批量改名")
    p_rename.add_argument("folder", help="目标文件夹路径")

    # archive - 需求3：归档与报告（在 feature/req3 中实现）
    p_archive = subparsers.add_parser("archive", help="按类别归档文件")
    p_archive.add_argument("folder", help="目标文件夹路径")

    # undo - 需求3：撤销（在 feature/req3 中实现）
    p_undo = subparsers.add_parser("undo", help="撤销上次操作")
    p_undo.add_argument("folder", help="目标文件夹路径")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    # 各子命令的实现由对应 feature 分支提供
    handler = _HANDLERS.get(args.command)
    if handler is None:
        print(f"子命令 '{args.command}' 尚未实现", file=sys.stderr)
        return 1
    return handler(args)


# 子命令处理器注册表（各 feature 分支会填充）
_HANDLERS: dict = {}


if __name__ == "__main__":
    sys.exit(main())
