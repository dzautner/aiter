# aiter
![image](https://github.com/user-attachments/assets/9457804f-77cd-44b0-a088-992e4b9971c6)


AITER is AMD’s centralized repository that support various of high performance AI operators for AI workloads acceleration, where a good unified place for all the customer operator-level requests, which can match different customers' needs. Developers can focus on operators, and let the customers integrate this op collection into their own private/public/whatever framework.
 

Some summary of the features:
* C++ level API
* Python level API
* The underneath kernel could come from triton/ck/asm
* Not just inference kernels, but also training kernels and GEMM+communication kernels—allowing for workarounds in any kernel-framework combination for any architecture limitation.



## Installation
```
git clone --recursive https://github.com/ROCm/aiter.git
cd aiter
python3 setup.py develop
```

If you happen to forget the `--recursive` during `clone`, you can use the following command after `cd aiter`
```
git submodule sync && git submodule update --init --recursive
```

### Cache directory

AITER now resolves its cache directory dynamically. By default it follows your platform conventions—`$XDG_CACHE_HOME/aiter` on Linux, `~/Library/Caches/aiter` on macOS, and `%LOCALAPPDATA%\Aiter\Cache` on Windows—with automatic migration from the legacy `~/.aiter` folder on first use. You can override the location with the `AITER_CACHE_HOME` environment variable (or `AITER_JIT_DIR` for the JIT staging tree) before running any AITER commands:

```
export AITER_CACHE_HOME=/raid/aiter-cache
python3 op_tests/test_layernorm2d.py
```

Existing overrides that relied on `AITER_ROOT_DIR` continue to work, but new deployments should prefer `AITER_CACHE_HOME` for clarity.

### LUMI build helper

LUMI users can lean on `scripts/lumi_build.sh` to load the recommended module stack, export `GPU_ARCHS=gfx90a`, point `AITER_CACHE_HOME` at `/scratch/<proj>/aiter_cache`, and run the editable install:

```
salloc --account=<proj> --partition=small-g --nodes=1 --gpus-per-node=1 --time=02:00:00
srun --pty bash
cd /projappl/<proj>/aiter
scripts/lumi_build.sh --project <proj>
```

Customize cache or virtualenv locations with `--cache-dir` and `--venv` if needed. Install a ROCm-enabled PyTorch wheel in that virtualenv ahead of time (or pass `--torch-wheel <url>` to the script) and the helper will also auto-load a recent Python module (configurable via `AITER_PYTHON_MODULE=<module>`) so newer wheels such as `pybind11>=3.0.1` install cleanly.

## Run operators supported by aiter

There are number of op test, you can run them with: `python3 op_tests/test_layernorm2d.py`
|  **Ops**                      | **Description**                                                                                                                                                   |
|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|ELEMENT WISE                   | ops: + - * /                                                                                                                                                      |
|SIGMOID                        | (x) = 1 / (1 + e^-x)                                                                                                                                              |
|AllREDUCE                      | Reduce + Broadcast                                                                                                                                                |
|KVCACHE                        | W_K W_V                                                                                                                                                           |
|MHA                            | Multi-Head Attention                                                                                                                                              |
|MLA                            | Multi-head Latent Attention with [KV-Cache layout](https://docs.flashinfer.ai/tutorials/kv_layout.html#page-table-layout )                                        |
|PA                             | Paged Attention                                                                                                                                                   |
|FusedMoe                       | Mixture of Experts                                                                                                                                                |
|QUANT                          | BF16/FP16 -> FP8/INT4                                                                                                                                             |
|RMSNORM                        | root mean square                                                                                                                                                  |
|LAYERNORM                      | x = (x - u) / (σ2 + ϵ) e*0.5                                                                                                                                      |
|ROPE                           | Rotary Position Embedding                                                                                                                                         |
|GEMM                           | D=αAβB+C                                                                                                                                                          |
