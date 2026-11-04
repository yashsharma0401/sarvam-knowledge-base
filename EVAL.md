# Evaluation

## Benchmark and protocol

HotpotQA v1 distractor development tests natural questions with sentence-level evidence annotations over Wikipedia excerpts. Each row supplies the candidate articles. We use it to measure whether the context assembler can recover the annotated evidence inside those candidates. The dataset also supplies bridge and comparison labels, which let us see where title expansion helps or hurts. [Benchmark paper](https://aclanthology.org/D18-1259/) · [Snapshot and license](data/SOURCES.md)

Rows are eligible when their gold supporting sentences resolve to exactly two distinct document titles and all original offsets resolve to nonblank text. We reject duplicate titles within a candidate set. Within each question type, sort by ascending SHA-256 of the question ID. Use the first 160 bridge and 40 comparison rows for the pilot, then the next 640 and 160 for evaluation. The bundled data contains all candidate documents and labels for these rows. The evaluation split is held out by question from the pilot, and both are subsets of the public development split. Articles can recur across splits. The deterministic retrieval experiment uses no learned model.

All runs use the same candidates and six-sentence cap. The baselines are flat sentence BM25, document BM25 with title and text followed by sentence ranking, and a title-aware lexical ranker that adds entity mention features. The link ablation zeroes the link bonus and stops connector promotion in the proposed pair-scoring path. It gives the same results as the title-aware ranker by construction. This tests the combined effect of selecting and promoting cross-document mentions.

Complete supporting-fact recall is the primary metric. It counts a question only if all annotated title and sentence pairs are in the packet. Complete document recall isolates document selection. Fact recall and set F1 summarize partial recovery and precision. Answer metrics use HotpotQA normalization and set scoring over the union of claim citations. Joint F1 combines answer and citation precision and recall, with an abstention scored as zero. The official annotations may omit alternate valid evidence. [Official metric implementation](https://github.com/hotpotqa/hotpot/blob/master/hotpot_evaluate_v1.py)

## Retrieval results

| Method | Both docs | All facts | Fact recall | Fact F1 | All facts, bridge | All facts, comparison |
|---|---:|---:|---:|---:|---:|---:|
| Sentence BM25 | 62.75% | 34.38% | 64.82% | 36.13% | 33.59% | 37.50% |
| Document BM25 | 39.38% | 36.88% | 65.83% | 41.23% | 35.00% | 44.38% |
| Title-aware BM25 | 48.13% | 45.25% | 70.27% | 43.95% | 35.16% | **85.63%** |
| Link ablation | 48.13% | 45.25% | 70.27% | 43.95% | 35.16% | **85.63%** |
| Link-aware | **73.25%** | **70.00%** | **83.26%** | **52.41%** | **67.34%** | 80.63% |

Link-aware retrieval gains **24.75 percentage points** on complete evidence against the strongest tested baseline, with a paired percentile bootstrap interval of **21.50 to 28.13 points** over 2,000 resamples with seed 42. It wins on 210 examples and loses on 12. Bridge questions gain 32.19 points, while comparison questions lose 5.00 points. The overall estimate uses this benchmark mix. The interval quantifies resampling variability over questions and does not account for repeated source articles.

## Offline synthesis check

The offline birth-order check takes all seven comparison rows in the evaluation split matching the question pattern `born (first|earlier|later)`. This is an exploratory cohort chosen after inspecting the available question formats. It is too small for a general answer-quality claim. The same answerer runs on every retrieval method, and the raw outputs retain all sources and the validated response.

| Method | Answer EM | Answer F1 | Citation F1 | Joint F1 | Abstentions |
|---|---:|---:|---:|---:|---:|
| Sentence BM25 | 28.57% | 28.57% | 28.57% | 28.57% | 5/7 |
| Document BM25 | 14.29% | 14.29% | 14.29% | 14.29% | 6/7 |
| Title-aware BM25 | 42.86% | **62.45%** | **71.43%** | **62.45%** | 2/7 |
| Link ablation | 42.86% | **62.45%** | **71.43%** | **62.45%** | 2/7 |
| Link-aware | 42.86% | 51.02% | 57.14% | 51.02% | 3/7 |

For link-aware retrieval, all four emitted answers have birth-year premises visible in the exact cited sentences, and the year ordering supports the returned person. Three match the benchmark answer exactly. The Elswyth Thane response uses the article title while the benchmark expects her full name, Helen Elswyth Thane Ricker Beebe. This manual check covers the four emitted offline answers and says nothing about broader model generation.

## Paired Ollama synthesis

The first 16 bridge and first four comparison rows in the evaluation split form this 20-question exploratory run. The two methods use the same six-sentence cap, question order, prompt, model and generation settings. The run used Ollama 0.35.0 and Qwen2.5 3B Q4_K_M with manifest SHA-256 `357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`, seed 42, temperature 0, a 4,096-token context, and a 512-token generation cap. The structured run took 1 minute 49 seconds on the development Mac. [Ollama model card](https://ollama.com/library/qwen2.5:3b)

| Retrieval method | All facts in packet | Answer EM | Answer F1 | Citation F1 | Joint EM | Joint F1 | Invalid |
|---|---:|---:|---:|---:|---:|---:|---:|
| Title-aware BM25 | 40.00% | 25.00% | 32.50% | 40.83% | 10.00% | 24.76% | 6/20 |
| Link-aware | 65.00% | 35.00% | 43.85% | 58.18% | 20.00% | 37.20% | 2/20 |

The first run used JSON mode and a prompt requiring the answer to be repeated as a claim. All 40 responses failed validation, commonly because the model emitted `citation` in place of `citations` or omitted the answer claim. The structured run uses an explicit answer-citation field and constrains citation IDs to the packet. Both retrieval methods were rerun on the same questions. Since the output contract was revised after observing the first run on this cohort, treat the synthesis figures as exploratory. The original and structured outputs are preserved in `results/ollama.jsonl` and `results/ollama-structured.jsonl`. The original prompt is in commit `3394627`. The first attempt with the installed 22 GB Qwen3.6 model timed out before producing a response. Both scored runs use Qwen2.5 3B.

In the Ben Ainslie case, both methods produce the right name. The baseline cites Bushell's tip list and an unrelated motorsport sentence. The link-aware method cites the tip list and Ainslie's article identifying him as an English competitive sailor. Only the link-aware answer earns joint exact match. In the Alexandra Park case (`5a84800f554299123d8c2276`), the two citations support the Cotton Famine date range, but the answer uses the expanded form `1861–1865` while the benchmark expects `1861–65`. Exact match counts it as wrong.

Citation integrity is weaker than grounding. For `5ae537a855429960a22e0266`, the linked packet includes a UK release location and album recording history. The model answers “United Kingdom” when asked where the duo was from. Neither passage establishes the duo's origin, even though the response has valid citations from two distinct sources. This spot check establishes a concrete grounding failure. It does not estimate the overall rate of unsupported claims.

## Inspectable cases

- **Bridge recovered** (`5ac250aa5542992f1f2b384d`). Mike Bushell sentence 5 names Ben Ainslie among the people whose tips he features. Ben Ainslie sentence 0 identifies him as an English competitive sailor. The lexical baseline does not retrieve the two annotated facts together.
- **Both articles found, one fact missing** (`5a8332815542993344745fe9`). The packet retrieves CFL on TSN and Wendy's, but omits the Wendy's lead naming founder Dave Thomas. Document recall alone would mark the packet successful.
- **Alias collision** (`5a751bbe5542993748c897ba`). The method selects the film article and its nearly identically titled short story instead of the gold film and Tom Courtenay articles. The short story excerpt also names Courtenay as a cast member, so the packet contains alternate support. This is a failure against the benchmark annotations.
- **Answerer abstains with both facts present** (`5a7c66d555429935c91b518f`). The Havel article's lead contains adjacent birth and death date fragments without a usable separator. The parser declines to compare it with Fitzgerald's year.

Raw outputs and rebuilt summaries are in [results/](results/). Run `./reproduce.sh` to regenerate the offline experiments and rescore the saved model outputs. With the pinned model installed and Ollama running, use `./reproduce.sh --fresh-ollama` to regenerate model outputs and rebuild their summary in the same command. Run `python3 -m kb score results/birth-order.jsonl` to independently reparse and rescore the saved answer records.
