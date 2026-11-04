"""Command line entry point."""
import argparse
import json
from pathlib import Path

from .data import load, select
from .evaluation import evaluate, output, rebuild
from .retrieval import Index, METHODS

parser = argparse.ArgumentParser(prog="python3 -m kb")
sub = parser.add_subparsers(dest="command", required=True)
prepare = sub.add_parser("prepare")
prepare.add_argument("source", type=Path)
rescore = sub.add_parser("score")
rescore.add_argument("raw", type=Path)
for command in ("eval", "ask"):
    run = sub.add_parser(command)
    answerer = run.add_mutually_exclusive_group()
    answerer.add_argument("--model", help="Ollama model tag")
    answerer.add_argument("--birth-order", action="store_true", help="Offline birth comparison")
    run.add_argument("--endpoint", default="http://127.0.0.1:11434")
    run.add_argument("--budget", type=int, default=6)
    if command == "eval":
        run.add_argument("--split", choices=("pilot", "test"), default="test")
        run.add_argument("--limit", type=int)
        run.add_argument("--out", type=Path)
    else:
        run.add_argument("id", nargs="?")
        run.add_argument("--documents", type=Path, help="JSON array of [title, [sentences]]")
        run.add_argument("--question")
        run.add_argument("--method", choices=METHODS, default="linked")

args = parser.parse_args()
if args.command == "prepare":
    select(args.source)
elif args.command == "score":
    print(json.dumps(rebuild(args.raw), indent=2))
elif args.command == "eval":
    default = "model" if args.model else "birth-order" if args.birth_order else "retrieval"
    print(json.dumps(evaluate(args.out or Path(f"results/{default}.jsonl"), args.split, args.budget, args.model, args.endpoint,
                              args.limit, args.birth_order), indent=2))
else:
    if args.documents:
        if not args.question or args.id:
            parser.error("Use --documents with --question")
        row = {"_id": "local", "type": "local", "question": args.question,
               "context": json.loads(args.documents.read_text()), "answer": "",
               "supporting_facts": []}
    else:
        snapshot = load()
        row = next((r for r in snapshot["pilot"] + snapshot["test"] if r["_id"] == args.id), None)
        if row is None:
            parser.error("Provide an ID from the bundled benchmark or --documents and --question")
    record = output(row, Index(row["context"]), args.method, args.budget, args.model, args.endpoint,
                    args.birth_order)
    for key in ("gold_answer", "gold_facts", "raw"):
        record.pop(key, None)
    print(json.dumps(record, ensure_ascii=False, indent=2))
