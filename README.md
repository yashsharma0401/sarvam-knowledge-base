# Knowledge Base as a Context Layer

A sentence-level evidence index and link-aware context assembler for multi-document questions. The offline experiment recovers all annotated evidence on **70.00% of 800 HotpotQA questions**, compared with **45.25%** for the strongest tested lexical baseline. The deterministic answerer covers birth-order comparisons and abstains outside that scope. See [EVAL.md](EVAL.md) for answer results and the comparison regression.

## Run it

Use Python 3.9 or newer and a POSIX shell. There are no Python dependencies, API keys, or downloads for the bundled run.

```sh
./reproduce.sh
```

This runs the tests, ingests the bundled Wikipedia excerpts, regenerates both raw JSONL runs, and rebuilds the JSON summaries from those outputs. The measured run took about 4 seconds on the development Mac. API cost is zero.

```sh
# Show the two-document evidence packet for a bridge question
python3 -m kb ask 5ac250aa5542992f1f2b384d

# Answer a birth-order question with exact source sentences
python3 -m kb ask 5a7744e45542993569682d37 --birth-order

# Show an abstention with both documents present
python3 -m kb ask 5a7c66d555429935c91b518f --birth-order

# Independently rescore a raw artifact
python3 -m kb score results/retrieval.jsonl
python3 -m kb score results/birth-order.jsonl
```

Supply your own candidate documents using a UTF-8 JSON array of `[title, [sentences]]` entries. Each title must be unique within the candidate set. Original array offsets are the citation coordinates.

```sh
python3 -m kb ask --documents corpus.json \
  --question 'Who was born first, Person A or Person B?' --birth-order
```

A citation such as `S3` resolves through the response's `evidence` map to the original document title, zero-based sentence index, and verbatim sentence with outer whitespace trimmed. The ID is local to that packet. The stable coordinate within the snapshot is the title and sentence index in the context of the question ID.

## Rebuild the input snapshot

The checked-in subset is derived from HotpotQA v1 distractor development data. The official download and the verified mirror are listed in [data/SOURCES.md](data/SOURCES.md). Given either pinned file:

```sh
python3 -m kb prepare /path/to/hotpot_dev_distractor_v1.json
./reproduce.sh
```

The loader checks the input SHA-256 before selecting any rows. See [EVAL.md](EVAL.md) for the exact selection rule.

## Experimental local model adapter

With Ollama already running and a model already installed, pass its tag to the shared synthesis interface. The adapter requests structured claims and checks their citation IDs. The offline results in this repo do not use this adapter. Its local inference run was declined, so model quality, runtime, and compatibility with the installed tag remain unverified.

```sh
python3 -m kb ask 5ac250aa5542992f1f2b384d --model qwen3.6:latest
python3 -m kb eval --model qwen3.6:latest --limit 20 --out results/model.jsonl
```

The model experiment compares title-aware retrieval and link-aware retrieval on the same subset. It stores model text and validation errors. Completed rows can be reused when the tag and evidence packet match. Runtime depends on local hardware and model size.

[DESIGN.md](DESIGN.md) covers architecture and tradeoffs. [WALKTHROUGH.md](WALKTHROUGH.md) is the live demo runbook.
