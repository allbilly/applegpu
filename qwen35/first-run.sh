#!/bin/sh
set -eu
qwen_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
qwen_runtime="$qwen_root/../gpt2"
qwen_python=${GPT2_PYTHON:-/usr/bin/python3}
qwen_backend=mlx
if [ "${1:-}" = benchmark ]; then qwen_backend=all; fi
qwen_previous=
for qwen_argument in "$@"; do
    if [ "$qwen_previous" = --backend ]; then qwen_backend=$qwen_argument; fi
    case "$qwen_argument" in --backend=*) qwen_backend=${qwen_argument#--backend=} ;; esac
    qwen_previous=$qwen_argument
done
qwen_cache=${XDG_CACHE_HOME:-"$HOME/.cache"}/applegpu-gpt2
if [ -d "$qwen_cache/runtime/usr/lib64" ]; then
    export LD_LIBRARY_PATH="$qwen_cache/runtime/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
"$qwen_python" "$qwen_runtime/bootstrap.py" --backend "$qwen_backend"
if [ -d "$qwen_cache/runtime/usr/lib64" ]; then
    export LD_LIBRARY_PATH="$qwen_cache/runtime/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
"$qwen_runtime/.venv/bin/python" "$qwen_root/bootstrap.py"
case "${1:-}" in
    verify|benchmark)
        qwen_tool=$1
        shift
        exec "$qwen_runtime/.venv/bin/python" "$qwen_root/tools/$qwen_tool.py" "$@" ;;
esac
exec "$qwen_runtime/.venv/bin/python" "$qwen_root/qwen35.py" "$@"
