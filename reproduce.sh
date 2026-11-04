#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m unittest discover -s tests
python3 -m kb eval --out results/retrieval.jsonl >/dev/null
python3 -m kb eval --birth-order --out results/birth-order.jsonl >/dev/null
printf '%s\n' 'Wrote raw outputs and rebuilt summaries in results/.'
