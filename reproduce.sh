#!/bin/sh
set -eu
cd "$(dirname "$0")"
case "${1:-}" in
    ""|--fresh-ollama) ;;
    *) printf '%s\n' 'Usage: ./reproduce.sh [--fresh-ollama]' >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
    printf '%s\n' 'Usage: ./reproduce.sh [--fresh-ollama]' >&2
    exit 2
fi
python3 -m unittest discover -s tests
python3 -m kb eval --out results/retrieval.jsonl >/dev/null
python3 -m kb eval --birth-order --out results/birth-order.jsonl >/dev/null
for raw in results/ollama.jsonl results/ollama-structured.jsonl; do
    if [ -s "$raw" ]; then
        python3 -m kb score "$raw" >/dev/null
    fi
done
if [ "${1:-}" = "--fresh-ollama" ]; then
    run_dir=$(mktemp -d results/ollama-run.XXXXXX)
    printf 'Writing fresh Ollama outputs to %s\n' "$run_dir"
    python3 -m kb eval --model qwen2.5:3b --limit 20 --out "$run_dir/raw.jsonl"
fi
printf '%s\n' 'Wrote raw outputs and rebuilt summaries in results/.'
