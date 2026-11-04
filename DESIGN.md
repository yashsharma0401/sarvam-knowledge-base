# Design

## Scope and data flow

The system treats the knowledge base as the layer between a set of candidate sources and an answerer. Its job is to decide which source sentences can support a multi-document answer within a small budget. The benchmark's candidate articles are real Wikipedia excerpts. A per-question candidate index isolates context selection from corpus-scale candidate generation, and the CLI accepts the same document format for new source sets. This approach fits a short, reproducible experiment on candidate reranking. Deployment over a growing corpus would need a persistent index and a first-stage candidate generator.

```text
Question + candidate articles
  -> ingest immutable title and sentence coordinates
  -> build document and sentence lexical indexes
  -> rank articles and identify possible cross-document mentions
  -> choose article pair and pack six evidence sentences
  -> compare documented birth years or call the experimental model adapter
  -> validate every claim reference and emit evidence alongside the answer
```

The unit of ingestion is a titled document with an ordered list of source sentences. Each sentence retains its position in the original array. Ingestion skips blank sentences and trims outer whitespace. Duplicate document titles are rejected because the citation coordinate would be ambiguous. The benchmark preserves the original text, including malformed punctuation and snapshot artifacts, in the bundled data. A production source ID should also include corpus ID and document revision.

## Retrieval and context assembly

The index builds three BM25 views over normalized Unicode tokens. One scores sentence text, one scores title plus sentence, and one scores article text with repeated title terms. Document frequency is computed within each candidate set. This is cheap and gives a tractable baseline on a fixed pool. It can miss paraphrases and morphological variants.

The title-aware ranker adds article-title coverage and exact alias occurrence in the question to the document score and best sentence score. It strips trailing parenthetical disambiguation from the alias while retaining the original title for citations. This allows questions naming a subject to find its article even when the relevant sentence uses a pronoun.

For each pair of documents, the link-aware ranker looks for one document's title alias in the other document's four strongest query-ranked sentences. It gives weight to a link when the destination alias is absent from the question and scales it by the source prior and mention sentence score. The highest-scoring pair wins. The connecting sentence moves to the front of its document's ranking. The packet alternates documents and fills any remaining capacity from the selected pair. This makes the connection itself visible to the answerer. It also makes exact title collisions and incidental mentions costly because an erroneous document can take half the evidence budget.

The budget is six sentences for all reported methods. Sentence count is a natural budget because the benchmark labels individual sentences. Exact token usage varies with sentence length, so the results describe a sentence-budget comparison. A production context builder would apply a token budget in addition to preserving whole citation spans.

## Synthesis and provenance

The offline answerer compares birth years when the question explicitly asks who was born first, earlier, or later. It matches two titles to the question, reads a birth marker or lifespan from each article's lead, and abstains when either source is absent, a year is unavailable, or the years tie. The answer cites both sentences. Each premise cites the source that supplies its year. The scope keeps the inference auditable, and also means this answerer covers a small part of the benchmark. Title aliases can disagree with the full names in benchmark answers.

The Ollama adapter exposes a broader synthesis interface. Its prompt treats retrieved text as data and asks for a short answer with evidence IDs for the answer and each premise. It uses an output schema whose citation IDs come from the current packet. The shared validator rejects malformed claims and unknown IDs, and requires the answer claim to cite two distinct titles. These constraints enforce citation integrity. A model can still attach a valid ID from an irrelevant sentence. The paired local experiment and grounding examples in EVAL.md measure that distinction.

The JSON response carries a complete evidence catalog. Packet labels such as S2 are presentation handles. Each label resolves to the document title, zero-based index, and source text, so a reviewer can verify the exact span. For benchmark output, the question ID identifies the candidate snapshot. Gold answers and supporting facts are read by the evaluator and excluded from the answerer's input.

## Failure modes and next steps

Link traversal helps when the question leaves the second entity implicit, but the comparison split loses coverage because some questions already name both targets and unrelated mentions can displace one of them. A follow-up experiment should lock high-confidence matches for explicitly named targets and compare the result on a fresh slice. Ambiguous titles need entity disambiguation before promotion. Missing supporting sentences within the right documents call for a sentence selector that scores the requested relation, such as a founding event, in addition to lexical overlap.

A persistent corpus introduces stable document identity, indexing across revisions, and candidate recall as separate concerns. An evaluation for that deployment would index an independently defined Wikipedia snapshot and report first-stage recall as well as downstream evidence recall. Broader synthesis needs a fixed model revision, a larger paired sample, and a claim-level entailment audit. The offline comparison and retrieval experiments in this repository measure narrower properties.
