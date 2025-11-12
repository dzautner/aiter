# SPDX-License-Identifier: MIT
# Copyright (C) 2024-2025, Advanced Micro Devices, Inc. All rights reserved.

from __future__ import annotations

import datetime
import logging
import os
import platform
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .file_baton import FileBaton

logger = logging.getLogger("aiter")


@dataclass(frozen=True)
class CacheLayout:
    """Materialized directories used by aiter for caches and build artifacts."""

    root: Path
    build_dir: Path
    jit_dir: Path
    logs_dir: Path
    configs_dir: Path


_cache_layout: Optional[CacheLayout] = None
_cache_lock = threading.Lock()
_legacy_home = Path.home() / ".aiter"


def _expand(path_like: Path | str) -> Path:
    return Path(path_like).expanduser().resolve()


def _platform_cache_default() -> Path:
    system = platform.system()
    if system == "Windows":
        base = (
            os.getenv("AITER_WINDOWS_CACHE", "")
            or os.getenv("LOCALAPPDATA", "")
            or os.getenv("APPDATA", "")
        )
        if base:
            return _expand(Path(base) / "Aiter" / "Cache")
        return _expand(Path.home() / "AppData" / "Local" / "Aiter" / "Cache")

    if system == "Darwin":
        return _expand(Path.home() / "Library" / "Caches" / "aiter")

    xdg_cache = os.getenv("XDG_CACHE_HOME")
    if xdg_cache:
        return _expand(Path(xdg_cache) / "aiter")

    return _expand(Path.home() / ".cache" / "aiter")


def _determine_cache_home(explicit: Optional[str]) -> Path:
    if explicit:
        return _expand(explicit)

    env_cache = os.getenv("AITER_CACHE_HOME")
    if env_cache:
        return _expand(env_cache)

    legacy_root_env = os.getenv("AITER_ROOT_DIR")
    if legacy_root_env:
        return _expand(Path(legacy_root_env) / ".aiter")

    candidate = _platform_cache_default()
    if candidate.exists() or candidate.parent.exists():
        return candidate

    return _expand(_legacy_home)


def _maybe_migrate_legacy_cache(target: Path) -> None:
    if os.getenv("AITER_CACHE_HOME") or os.getenv("AITER_ROOT_DIR"):
        return

    if not _legacy_home.exists() or target == _legacy_home:
        return

    if target.exists() and any(target.iterdir()):
        return

    lock_path = _legacy_home.parent / ".aiter-cache-migrate.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    baton = FileBaton(str(lock_path))
    if not baton.try_acquire():
        baton.wait()
        return

    try:
        if not _legacy_home.exists():
            return

        if target.exists():
            if any(target.iterdir()):
                return
            target.rmdir()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(_legacy_home), str(target))
        marker = target / "CACHE_MIGRATED_FROM"
        timestamp = datetime.datetime.utcnow().isoformat() + "Z"
        marker.write_text(
            f"migrated_from={_legacy_home}\ncompleted_at={timestamp}\n",
            encoding="utf-8",
        )
        logger.info("migrated legacy cache from %s to %s", _legacy_home, target)
    finally:
        baton.release()


def _hydrate_layout(cache_home: Path) -> CacheLayout:
    cache_home.mkdir(parents=True, exist_ok=True)
    _maybe_migrate_legacy_cache(cache_home)

    layout = CacheLayout(
        root=cache_home,
        build_dir=cache_home / "build",
        jit_dir=cache_home / "jit",
        logs_dir=cache_home / "logs",
        configs_dir=cache_home / "configs",
    )

    for path in (layout.build_dir, layout.jit_dir, layout.logs_dir, layout.configs_dir):
        path.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("AITER_CACHE_HOME", str(layout.root))
    return layout


def get_cache_layout(explicit: Optional[str] = None) -> CacheLayout:
    """Return the singleton cache layout, resolving directories on first use."""

    global _cache_layout
    if _cache_layout is not None and explicit is None:
        return _cache_layout

    with _cache_lock:
        if _cache_layout is None or explicit is not None:
            cache_home = _determine_cache_home(explicit)
            _cache_layout = _hydrate_layout(cache_home)
    return _cache_layout


def get_cache_home() -> str:
    return str(get_cache_layout().root)


def reset_cache_layout_for_testing():  # pragma: no cover - testing helper
    global _cache_layout
    with _cache_lock:
        _cache_layout = None
