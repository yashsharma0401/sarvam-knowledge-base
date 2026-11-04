# Live walkthrough runbook

Allow about 6 minutes. Run the commands from the repository root.

1. **0:00–0:45** Explain the per-question candidate pool and the six-sentence budget. Show the input snapshot and point to the split and eligibility rules in EVAL.md.
2. **0:45–2:00** Compare the bridge question under the two retrieval methods. With Ollama running, show the cited answer. Read Mike Bushell sentence 5 and Ben Ainslie sentence 0. The saved structured run contains the same paired example for an offline walkthrough.

   ```sh
   python3 -m kb ask 5ac250aa5542992f1f2b384d --method title_bm25
   python3 -m kb ask 5ac250aa5542992f1f2b384d --model qwen2.5:3b
   ```

3. **2:00–3:15** Run the offline birth-order answer. Resolve each citation through the evidence map. Juan Rulfo's and John le Carré's birth years are in different articles. The answer claim cites both premises.

   ```sh
   python3 -m kb ask 5a7744e45542993569682d37 --birth-order
   ```

4. **3:15–4:15** Run the abstention case. Show the malformed Havel date and the empty claim list. Then show the founder example to distinguish sentence selection failures from parser failures.

   ```sh
   python3 -m kb ask 5a7c66d555429935c91b518f --birth-order
   python3 -m kb ask 5a8332815542993344745fe9
   ```

5. **4:15–6:00** Run the reproduction command. Open the summary and explain the 24.75-point gain, the link ablation, and the 5-point comparison regression. Close with the paired Ollama run, its small sample, and the UK release-location error as a case where two citations did not establish the answer.

   ```sh
   ./reproduce.sh
   python3 -m kb score results/retrieval.jsonl
   ```
