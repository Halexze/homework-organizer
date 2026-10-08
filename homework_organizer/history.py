"""操作历史记录，支持撤销"""

import json
from datetime import datetime
from pathlib import Path

HISTORY_FILENAME = ".organizer_history.json"


def history_path(folder: str) -> Path:
    """返回历史文件路径"""
    return Path(folder) / HISTORY_FILENAME


def load_history(folder: str) -> list[dict]:
    """加载历史记录列表"""
    path = history_path(folder)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_history(folder: str, records: list[dict]) -> None:
    """保存历史记录列表"""
    path = history_path(folder)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def record_operation(folder: str, operation: dict) -> None:
    """
    记录一次操作到历史中。

    Args:
        folder: 目标文件夹
        operation: 操作记录字典，需包含 type 和 moves
    """
    records = load_history(folder)
    operation = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        **operation,
    }
    records.append(operation)
    save_history(folder, records)


def pop_last_operation(folder: str) -> dict | None:
    """
    取出并删除最后一条操作记录。

    Returns:
        最后一条操作记录，如果没有则返回 None
    """
    records = load_history(folder)
    if not records:
        return None
    last = records.pop()
    save_history(folder, records)
    return last
