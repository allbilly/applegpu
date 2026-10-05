#!/bin/sh
set -eu
gpt2_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
gpt2_python=${GPT2_PYTHON:-/usr/bin/python3}
gpt2_cache=${XDG_CACHE_HOME:-"$HOME/.cache"}/applegpu-gpt2
gpt2_backend=tinygrad
gpt2_previous=
for gpt2_argument in "$@"; do
    if [ "$gpt2_previous" = --backend ]; then gpt2_backend=$gpt2_argument; fi
    case "$gpt2_argument" in
        --backend=*) gpt2_backend=${gpt2_argument#--backend=} ;;
    esac
    gpt2_previous=$gpt2_argument
done
if [ "${1:-}" = compare ]; then gpt2_backend=all; fi
if [ -d "$gpt2_cache/runtime/usr/lib64" ]; then
    export LD_LIBRARY_PATH="$gpt2_cache/runtime/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
"$gpt2_python" "$gpt2_root/bootstrap.py" --backend "$gpt2_backend"
# Bootstrap may have downloaded the libraries during this invocation.
if [ -d "$gpt2_cache/runtime/usr/lib64" ]; then
    export LD_LIBRARY_PATH="$gpt2_cache/runtime/usr/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-1}
if [ "${1:-}" = compare ]; then
    shift
    exec "$gpt2_root/.venv/bin/python" "$gpt2_root/compare.py" "$@"
fi
exec "$gpt2_root/.venv/bin/python" "$gpt2_root/gpt2.py" "$@"
