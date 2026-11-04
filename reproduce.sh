#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m unittest discover -s tests
python3 -m kb eval --out results/retrieval.jsonl >/dev/null
python3 -m kb eval --birth-order --out results/birth-order.jsonl >/dev/null
for raw in results/ollama.jsonl results/ollama-structured.jsonl; do
    if [ -s "$raw" ]; then
        python3 -m kb score "$raw" >/dev/null
    fi
done
printf '%s\n' 'Wrote raw outputs and rebuilt summaries in results/.'
