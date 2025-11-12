#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Helper to build/install AITER on LUMI GPU nodes.

set -euo pipefail

usage() {
    cat <<'USAGE'
Usage: scripts/lumi_build.sh --project <proj> [--cache-dir /scratch/proj/aiter_cache]

Requirements:
  * Run this inside an interactive GPU allocation (e.g. `salloc --partition=small-g ...; srun --pty bash`).
  * Execute from the root of the AITER repository.
  * Install PyTorch with ROCm support in the chosen virtualenv before running this script.

Options:
  --project <proj>    LUMI project ID (used to derive default cache path).
  --cache-dir <path>  Override cache directory (default: /scratch/<proj>/aiter_cache).
  --venv <path>       Reuse/create a Python venv path (default: .lumi-venv under the repo).
  --torch-wheel <url> Optional PyTorch ROCm wheel URL; the script will install it into the virtualenv.
USAGE
}

PROJECT=""
CACHE_DIR=""
VENV_DIR=".lumi-venv"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project)
            PROJECT="$2"
            shift 2
            ;;
        --cache-dir)
            CACHE_DIR="$2"
            shift 2
            ;;
        --venv)
            VENV_DIR="$2"
            shift 2
            ;;
        --torch-wheel)
            TORCH_WHEEL="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$PROJECT" ]]; then
    echo "ERROR: --project <proj> is required." >&2
    usage
    exit 1
fi

if [[ -z "${SLURM_JOB_ID:-}" ]]; then
    echo "WARNING: SLURM_JOB_ID is not set. Run inside 'srun --pty' on a GPU node." >&2
fi

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$REPO_ROOT"

module load LUMI/24.03
module load partition/G
module load PrgEnv-amd
module load rocm/6.0.3
module load craype-accel-amd-gfx90a
module load buildtools/24.03

if [[ -z "${AITER_PYTHON_MODULE:-}" ]]; then
    PYTHON_MODULE_CANDIDATES=(
        python/3.10.8
        cray-python/3.11.7
        cray-python
    )
else
    PYTHON_MODULE_CANDIDATES=("$AITER_PYTHON_MODULE")
fi

PYTHON_LOADED=""
for mod in "${PYTHON_MODULE_CANDIDATES[@]}"; do
    if module spider "$mod" >/dev/null 2>&1; then
        module load "$mod"
        PYTHON_LOADED="$mod"
        break
    fi
done

if [[ -z "$PYTHON_LOADED" ]]; then
    echo "WARNING: no preferred Python module available; falling back to system python $(python3 --version 2>/dev/null)." >&2
else
    echo "Loaded Python module: $PYTHON_LOADED"
fi

export GPU_ARCHS=${GPU_ARCHS:-gfx90a}
export MPICH_GPU_SUPPORT_ENABLED=${MPICH_GPU_SUPPORT_ENABLED:-1}

if [[ -z "$CACHE_DIR" ]]; then
    CACHE_DIR="/scratch/${PROJECT}/aiter_cache"
fi
mkdir -p "$CACHE_DIR"
export AITER_CACHE_HOME="$CACHE_DIR"

echo "Using cache dir: $AITER_CACHE_HOME"

PYTHON_BIN=$(command -v python3)
if [[ -z "$PYTHON_BIN" ]]; then
    echo "ERROR: python3 not found in PATH after loading modules." >&2
    exit 1
fi

MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10
if [[ -d "$VENV_DIR" ]]; then
    VENV_PY="$VENV_DIR/bin/python3"
    if [[ ! -x "$VENV_PY" ]] || ! "$VENV_PY" -c 'import sys' >/dev/null 2>&1 || \
       ! "$VENV_PY" -c "import sys; sys.exit(0 if (sys.version_info.major, sys.version_info.minor) >= ($MIN_PYTHON_MAJOR, $MIN_PYTHON_MINOR) else 1)"; then
        echo "Recreating virtualenv $VENV_DIR for Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}"
        rm -rf "$VENV_DIR"
    fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ! python -c "import torch" >/dev/null 2>&1; then
    if [[ -n "${TORCH_WHEEL:-}" ]]; then
        echo "Installing PyTorch from provided wheel: $TORCH_WHEEL"
        python -m pip install "$TORCH_WHEEL"
    else
        echo "ERROR: PyTorch is not installed in $VENV_DIR. Re-run with --torch-wheel <url> or preinstall torch manually." >&2
        exit 1
    fi
fi

python setup.py develop

echo "Build completed. Leave the allocation with 'exit' when done."
