# -*- coding: utf-8 -*-

"""
ソーシャル出力の保持方針適用（archive/delete）
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


def _parse_date_dir(name: str) -> Optional[datetime]:
    # 例: 20250829
    try:
        return datetime.strptime(name, "%Y%m%d")
    except Exception:
        return None


def _parse_note_file(name: str) -> Optional[datetime]:
    # 例: 2025-08-29.md
    try:
        stem = name
        if name.endswith(".md"):
            stem = name[:-3]
        return datetime.strptime(stem, "%Y-%m-%d")
    except Exception:
        return None


def apply_social_retention(base_dir: str, policy: str, days: int = 30) -> None:
    """build配下（social/note）の保持方針を適用

    Args:
        base_dir: 出力ベース（例: ./build）
        policy: keep | archive | delete
        days: 保持日数
    """
    policy = (policy or "keep").lower()
    if policy == "keep":
        return

    base = Path(base_dir)
    if not base.exists():
        return

    threshold = datetime.now() - timedelta(days=days)

    # social/YYYYMMDD ディレクトリ
    social_dir = base / "social"
    if social_dir.exists():
        for child in social_dir.iterdir():
            if not child.is_dir():
                continue
            dt = _parse_date_dir(child.name)
            if not dt or dt >= threshold:
                continue
            if policy == "delete":
                shutil.rmtree(child, ignore_errors=True)
            elif policy == "archive":
                archive_dst = Path("Archive/social") / child.name
                archive_dst.parent.mkdir(parents=True, exist_ok=True)
                # 既に存在する場合は上書き移動
                if archive_dst.exists():
                    shutil.rmtree(archive_dst, ignore_errors=True)
                shutil.move(str(child), str(archive_dst))

    # note/YYYY-MM-DD.md ファイル
    note_dir = base / "note"
    if note_dir.exists():
        for child in note_dir.iterdir():
            if not child.is_file():
                continue
            dt = _parse_note_file(child.name)
            if not dt or dt >= threshold:
                continue
            if policy == "delete":
                try:
                    child.unlink()
                except Exception:
                    pass
            elif policy == "archive":
                archive_dst = Path("Archive/note") / child.name
                archive_dst.parent.mkdir(parents=True, exist_ok=True)
                if archive_dst.exists():
                    try:
                        archive_dst.unlink()
                    except Exception:
                        pass
                shutil.move(str(child), str(archive_dst))

