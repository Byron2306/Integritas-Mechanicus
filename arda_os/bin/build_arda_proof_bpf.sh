#!/bin/bash
set -euo pipefail
if [ "$#" -ne 2 ]; then
    echo 'usage: build_arda_proof_bpf.sh SOURCE_DIRECTORY NEW_OUTPUT_DIRECTORY' >&2
    exit 2
fi
source_dir=$(realpath "$1")
output_dir=$2
if [ -e "$output_dir" ]; then
    echo 'output directory must not exist; preserve existing artifacts' >&2
    exit 1
fi
compiler=$(command -v clang || command -v clang-19)
mkdir -m 700 "$output_dir"
"$compiler" -O2 -g -target bpf -D__TARGET_ARCH_x86 -I"$source_dir" \
  -c "$source_dir/arda_physical_lsm.c" -o "$output_dir/arda_physical_lsm.o"
loader_source="$source_dir/arda_lsm_loader.c"

if [ ! -f "$loader_source" ]; then
    echo "missing canonical BPF loader source: $loader_source" >&2
    exit 1
fi

cc -O2 -Wall -Wextra "$loader_source" -lbpf \
  -o "$output_dir/arda_lsm_loader"

sha256sum "$output_dir/arda_physical_lsm.o" "$output_dir/arda_lsm_loader" \
  "$source_dir/arda_physical_lsm.c" "$loader_source" \
  > "$output_dir/artifacts.sha256"
