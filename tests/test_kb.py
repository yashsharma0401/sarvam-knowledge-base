import unittest

from kb.birth_order import solve
from kb.data import Sentence, ingest, load
from kb.evaluation import answer_score, score
from kb.retrieval import Index
from kb.synthesis import validate


class KnowledgeBaseTests(unittest.TestCase):
    def test_original_offsets_survive_blank_sentences(self):
        self.assertEqual(ingest([["Article", ["", " Evidence "]]])["Article"],
                         (Sentence("Article", 1, "Evidence"),))

    def test_snapshot_splits_are_disjoint(self):
        data = load()
        self.assertEqual(len(data["pilot"]), 200)
        self.assertEqual(len(data["test"]), 800)
        self.assertFalse({row["_id"] for row in data["pilot"]}
                         & {row["_id"] for row in data["test"]})

    def test_bridge_includes_both_annotated_sentences(self):
        row = next(row for row in load()["test"] if row["_id"] == "5ac250aa5542992f1f2b384d")
        packet = Index(row["context"]).retrieve(row["question"], "linked")
        self.assertLessEqual(len(packet), 6)
        self.assertTrue(set(map(tuple, row["supporting_facts"])) <= {s.location for s in packet})

    def test_birth_order_requires_two_distinct_sources(self):
        question = "Who was born first, Person A or Person B?"
        packet = [Sentence("Person A", 0, "Person A (1900–1970) was an engineer."),
                  Sentence("Person B", 0, "Person B (born 1920) is an engineer.")]
        result = solve(question, packet)
        self.assertEqual(validate(result, packet)["answer"], "Person A")
        self.assertEqual(solve(question, packet[:1])["answer"], "")
        result["claims"][0]["citations"] = ["S1", "S999"]
        with self.assertRaises(ValueError):
            validate(result, packet)

    def test_structured_answer_citations_use_two_distinct_sources(self):
        packet = [Sentence("First", 0, "First premise"),
                  Sentence("Second", 0, "Second premise")]
        raw = {"answer": "Result", "answer_citations": ["S1", "S2"], "claims": [
            {"text": "First premise", "citations": ["S1"]},
        ]}
        self.assertEqual(validate(raw, packet)["claims"][0],
                         {"text": "Result", "citations": ["S1", "S2"]})
        raw["answer_citations"] = ["S1", "S1"]
        with self.assertRaises(ValueError):
            validate(raw, packet)

    def test_yes_no_and_abstention_scoring(self):
        self.assertEqual(answer_score("no", "yes"), (0, 0, 0, 0))
        values = score({"evidence": {}, "gold_facts": [["A", 0], ["B", 0]], "gold_answer": "x",
                        "raw": '{"answer":"","claims":[]}'})
        self.assertTrue(values["abstained"])
        self.assertEqual(values["joint_f1"], 0)
