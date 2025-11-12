# SPDX-License-Identifier: MIT
# Copyright (C) 2025, Advanced Micro Devices, Inc. All rights reserved.

import importlib
import importlib.util
import os
import sys
import types
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _fresh_cache_module(monkeypatch, tmp_path, **env):
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    hipconfig_path = fake_bin / "hipconfig"
    hipconfig_path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo 6.1.0\n"
        "else\n"
        "  echo 6.1.0\n"
        "fi\n",
        encoding="utf-8",
    )
    hipconfig_path.chmod(0o755)
    rocminfo_path = fake_bin / "rocminfo"
    rocminfo_path.write_text(
        "#!/bin/sh\n"
        "echo 'GPU 0          : gfx942'\n",
        encoding="utf-8",
    )
    rocminfo_path.chmod(0o755)
    monkeypatch.setenv("PATH", f"{fake_bin}:{os.environ.get('PATH', '')}")

    for key in ("AITER_CACHE_HOME", "AITER_ROOT_DIR"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    for module_name in list(sys.modules.keys()):
        if module_name == "aiter" or module_name.startswith("aiter."):
            sys.modules.pop(module_name, None)

    package_paths = {
        "aiter": REPO_ROOT / "aiter",
        "aiter.jit": REPO_ROOT / "aiter" / "jit",
        "aiter.jit.utils": REPO_ROOT / "aiter" / "jit" / "utils",
    }
    for name, path in package_paths.items():
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module

    cache_path = REPO_ROOT / "aiter" / "jit" / "utils" / "cache_dir.py"
    spec = importlib.util.spec_from_file_location(
        "aiter.jit.utils.cache_dir", cache_path, submodule_search_locations=[str(cache_path.parent)]
    )
    cache_dir = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = cache_dir
    assert spec.loader is not None
    spec.loader.exec_module(cache_dir)

    cache_dir.reset_cache_layout_for_testing()
    return cache_dir


def test_cache_layout_uses_env_override(tmp_path, monkeypatch):
    cache_home = tmp_path / "custom" / "cache"
    cache_dir = _fresh_cache_module(
        monkeypatch, tmp_path, AITER_CACHE_HOME=str(cache_home)
    )

    layout = cache_dir.get_cache_layout()

    assert layout.root == cache_home.resolve()
    for child in ("build", "jit", "logs", "configs"):
        assert (layout.root / child).exists()


def test_cache_layout_falls_back_to_legacy_root(tmp_path, monkeypatch):
    legacy_root = tmp_path / "legacy"
    cache_dir = _fresh_cache_module(monkeypatch, tmp_path, AITER_ROOT_DIR=str(legacy_root))

    layout = cache_dir.get_cache_layout()

    expected = (legacy_root / ".aiter").resolve()
    assert layout.root == expected
    assert layout.build_dir == expected / "build"
