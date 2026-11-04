"""Write per-question outputs and independently score them."""
import json
import random
import re
import string
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from .birth_order import QUESTION, solve
from .data import Sentence, load
from .retrieval import Index, METHODS
from .synthesis import catalog, generate, validate

def normalize(text):
    text = "".join(char for char in text.lower() if char not in string.punctuation)
    return re.sub(r"\b(a|an|the)\b", " ", text).split()


def answer_score(prediction, gold):
    left, right = normalize(prediction), normalize(gold)
    exact = float(left == right)
    if left != right and any(tokens in (["yes"], ["no"], ["noanswer"]) for tokens in (left, right)):
        return exact, 0, 0, 0
    common = sum((Counter(left) & Counter(right)).values())
    return exact, common / max(1, len(left)), common / max(1, len(right)), (
        2 * common / max(1, len(left) + len(right))
    )


def facts_score(prediction, gold):
    hits = len(prediction & gold)
    return (float(prediction == gold), hits / max(1, len(prediction)), hits / len(gold),
            2 * hits / (len(prediction) + len(gold)))


def output(row, index, method, budget, model=None, endpoint=None, birth_order=False):
    packet = index.retrieve(row["question"], method, budget)
    record = {"id": row["_id"], "kind": row["type"], "method": method,
              "question": row["question"], "gold_answer": row["answer"],
              "gold_facts": row["supporting_facts"], "evidence": catalog(packet)}
    if model or birth_order:
        raw = (json.dumps(solve(row["question"], packet)) if birth_order
               else generate(row["question"], packet, model, endpoint))
        record.update(model="birth_order" if birth_order else model, raw=raw)
        record["response"], error = parse_answer(raw, packet)
        if error:
            record["validation_error"] = error
    return record


def parse_answer(raw, packet):
    try:
        return validate(json.loads(raw), packet), None
    except ValueError as error:
        return {"answer": "", "claims": []}, str(error)


def score(record):
    evidence = record["evidence"]
    gold = {tuple(fact) for fact in record["gold_facts"]}
    locations = {key: (value["title"], value["sentence"]) for key, value in evidence.items()}
    predicted = set(locations.values())
    scores = {
        "complete_docs": {title for title, _ in gold} <= {title for title, _ in predicted},
        "complete_facts": gold <= predicted,
        "fact_recall": len(gold & predicted) / len(gold),
        "fact_f1": facts_score(predicted, gold)[3],
    }
    if "raw" in record:
        packet = [Sentence(value["title"], value["sentence"], value["text"])
                  for value in evidence.values()]
        if list(evidence) != list(catalog(packet)):
            raise ValueError("Raw evidence IDs are not in packet order")
        response, error = parse_answer(record["raw"], packet)
        cited = {locations[ref] for claim in response["claims"] for ref in claim["citations"]}
        ae, ap, ar, af = answer_score(response["answer"], record["gold_answer"])
        ce, cp, cr, cf = facts_score(cited, gold)
        precision, recall = ap * cp, ar * cr
        scores.update(answer_em=ae, answer_f1=af, citation_f1=cf, joint_em=ae * ce,
                      joint_f1=2 * precision * recall / (precision + recall)
                      if precision + recall else 0,
                      abstained=not response["answer"], invalid=error is not None)
    return scores


def paired_interval(deltas, samples=2000):
    rng = random.Random(42)
    estimates = sorted(mean(rng.choices(deltas, k=len(deltas))) for _ in range(samples))
    return [estimates[int(samples * .025)], estimates[int(samples * .975) - 1]]


def report(records):
    grouped = defaultdict(list)
    by_method = defaultdict(dict)
    for record in records:
        values = score(record)
        method = record["method"]
        grouped[method, "all"].append(values)
        grouped[method, record["kind"]].append(values)
        if record["id"] in by_method[method]:
            raise ValueError(f"Duplicate output for {method} / {record['id']}")
        by_method[method][record["id"]] = values
    result = {"metrics": {}, "paired_vs_linked": {}}
    for (method, kind), values in sorted(grouped.items()):
        result["metrics"].setdefault(method, {})[kind] = {
            "n": len(values), **{metric: mean(row[metric] for row in values) for metric in values[0]}
        }
    linked = by_method.get("linked", {})
    for method, baseline in sorted(by_method.items()):
        if method == "linked" or not linked or baseline.keys() != linked.keys():
            continue
        deltas = [int(linked[key]["complete_facts"]) - int(baseline[key]["complete_facts"])
                  for key in sorted(linked)]
        result["paired_vs_linked"][method] = {
            "complete_facts_delta": mean(deltas), "bootstrap_95": paired_interval(deltas),
            "wins": deltas.count(1), "losses": deltas.count(-1),
        }
    return result


def evaluate(path, split, budget, model, endpoint, limit, birth_order=False):
    rows = load()[split]
    if birth_order:
        rows = [r for r in rows if r["type"] == "comparison" and QUESTION.search(r["question"])]
    if limit is not None:
        if not 0 < limit <= len(rows):
            raise ValueError("Limit must be positive and no larger than the selected split")
        buckets = [[r for r in rows if r["type"] == kind] for kind in ("bridge", "comparison")]
        comparison_count = min(len(buckets[1]), max(1, limit // 5)) if limit > 1 else 0
        bridge_count = min(len(buckets[0]), limit - comparison_count)
        rows = buckets[0][:bridge_count] + buckets[1][:limit - bridge_count]
    methods = ("title_bm25", "linked") if model else METHODS
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if model and path.exists():
        for line in path.read_text().splitlines():
            record = json.loads(line)
            existing[record["id"], record["method"]] = record
    expected = {(row["_id"], method) for row in rows for method in methods}
    if not existing.keys() <= expected:
        raise ValueError("Cached examples differ from this run. Use a new output file.")
    with path.open("a" if existing else "w", encoding="utf-8", buffering=1) as stream:
        for row in rows:
            index = Index(row["context"])
            for method in methods:
                key = row["_id"], method
                if key in existing:
                    record = existing[key]
                    packet = catalog(index.retrieve(row["question"], method, budget))
                    if record["model"] != model or record["evidence"] != packet:
                        raise ValueError("Cached model or evidence differs. Use a new output file.")
                    continue
                record = output(row, index, method, budget, model, endpoint, birth_order)
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                if model:
                    print(f"{key[0]} {method}: {record['response']['answer'] or '[abstained]'}",
                          flush=True)
    return rebuild(path)


def rebuild(path):
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    result = report(records)
    path.with_suffix(".summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
