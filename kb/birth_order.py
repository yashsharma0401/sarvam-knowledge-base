"""Deterministic synthesis for a narrow, auditable comparison family."""
import re
from collections import defaultdict

from .retrieval import name, phrase
from .synthesis import catalog

QUESTION = re.compile(r"\bborn (first|earlier|later)\b", re.IGNORECASE)
YEAR = r"(?<!\d)([12]\d{3})(?!\d)"
BORN = re.compile(r"\bborn\s+[^(),;]*?" + YEAR, re.IGNORECASE)
LIFESPAN = re.compile(
    r"\([^()]{0,55}?" + YEAR + r"[^()–—]{0,45}[–—-][^()]{0,55}?" + YEAR + r"[^()]*\)"
)


def solve(question, packet):
    empty = {"answer": "", "claims": []}
    match = QUESTION.search(question)
    if match is None:
        return empty
    question_phrase = phrase(question)
    sources = defaultdict(list)
    for ref, sentence in catalog(packet).items():
        title = sentence["title"]
        if phrase(name(title)) in question_phrase:
            sources[title].append((ref, sentence))
    if len(sources) != 2:
        return empty

    premises = []
    for title, entries in sources.items():
        years = {}
        for ref, sentence in entries:
            # A biography lead has the subject as its implicit focus. Later
            # sentences can describe relatives or another person's birth.
            if sentence["sentence"] != 0:
                continue
            text = sentence["text"]
            # Interpret explicit birth markers only in the subject's lead,
            # before the sentence moves into biographical details.
            lead = re.split(r"\b(?:is|was|were)\b", text, maxsplit=1)[0]
            dated = BORN.search(lead) or LIFESPAN.search(lead)
            if dated:
                years[int(dated[1])] = ref
        if len(years) != 1:
            return empty
        year, ref = next(iter(years.items()))
        premises.append((year, name(title), ref))
    if premises[0][0] == premises[1][0]:
        return empty
    ordered = sorted(premises, reverse=match[1].lower() == "later")
    answer = ordered[0][1]
    return {
        "answer": answer,
        "claims": [
            {"text": answer, "citations": [ref for _, _, ref in ordered]},
            *({"text": f"{person} was born in {year}.", "citations": [ref]}
              for year, person, ref in ordered),
        ],
    }
