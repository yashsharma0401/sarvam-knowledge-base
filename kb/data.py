"""Snapshot ingestion and deterministic benchmark selection."""
import gzip
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/hotpot-subset.json.gz"
SOURCE_HASHES = {
    "4e9ecb5c8d3b719f624d66b60f8d56bf227f03914f5f0753d6fa1b359d7104ea",
    "e3da074df24e8369009918aa5cdbdd254dadcde4c63f7569d36afd6f2268caa8",
}


@dataclass(frozen=True)
class Sentence:
    title: str
    offset: int
    text: str

    @property
    def location(self):
        return self.title, self.offset


def ingest(context):
    documents = {}
    for title, sentences in context:
        if title in documents:
            raise ValueError(f"Duplicate document title: {title}")
        documents[title] = tuple(
            Sentence(title, offset, text.strip())
            for offset, text in enumerate(sentences) if text.strip()
        )
    return documents


def eligible(row):
    context = dict(row["context"])
    facts = row["supporting_facts"]
    return (
        len(context) == len(row["context"])
        and len({title for title, _ in facts}) == 2
        and all(title in context and 0 <= offset < len(context[title])
                and context[title][offset].strip() for title, offset in facts)
    )


def select(source):
    payload = Path(source).read_bytes()
    checksum = hashlib.sha256(payload).hexdigest()
    if checksum not in SOURCE_HASHES:
        raise ValueError(f"Unexpected dataset checksum: {checksum}")
    rows = json.loads(payload)
    subsets = {"pilot": [], "test": []}
    for kind, pilot_size, test_size in (("bridge", 160, 640), ("comparison", 40, 160)):
        ranked = sorted(
            (row for row in rows if row["type"] == kind and eligible(row)),
            key=lambda row: hashlib.sha256(row["_id"].encode()).digest(),
        )
        subsets["pilot"].extend(ranked[:pilot_size])
        subsets["test"].extend(ranked[pilot_size:pilot_size + test_size])
    snapshot = {"source_sha256": checksum, **subsets}
    SNAPSHOT.write_bytes(gzip.compress(json.dumps(snapshot, ensure_ascii=False,
                                                   separators=(",", ":")).encode(), mtime=0))


def load():
    with gzip.open(SNAPSHOT, "rt", encoding="utf-8") as stream:
        return json.load(stream)
