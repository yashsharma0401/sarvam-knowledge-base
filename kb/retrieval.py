"""Lexical baselines and evidence-conditioned passage selection."""
import math
import re
import unicodedata
from collections import Counter
from itertools import combinations

from .data import ingest

STOP = set(("a an and are as at be been both by did do does for from had has have how in "
            "is it its of on or that the their this to was were what when where which who "
            "whose with would").split())
METHODS = ("sentence_bm25", "document_bm25", "title_bm25", "no_links", "linked")


def words(text):
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold())


def terms(text):
    return [word for word in words(text) if word not in STOP]


def phrase(text):
    return " " + " ".join(words(text)) + " "


def name(title):
    return re.sub(r"\s*\([^()]+\)$", "", title)


class BM25:
    def __init__(self, corpus):
        self.counts = [Counter(tokens) for tokens in corpus]
        self.lengths = [sum(count.values()) for count in self.counts]
        average = sum(self.lengths) / max(1, len(self.lengths))
        self.norms = [1.2 * (.25 + .75 * length / max(average, 1))
                      for length in self.lengths]
        df = Counter(word for counts in self.counts for word in counts)
        self.idf = {word: math.log1p((len(corpus) - n + .5) / (n + .5))
                    for word, n in df.items()}

    def score(self, query):
        return [
            sum(self.idf[word] * 2.2 * counts[word] / (counts[word] + norm)
                for word in sorted(set(query) & counts.keys()))
            for counts, norm in zip(self.counts, self.norms)
        ]


class Index:
    def __init__(self, context):
        self.docs = {title: sentences for title, sentences in ingest(context).items()
                     if sentences}
        self.titles = list(self.docs)
        self.sentences = [sentence for doc in self.docs.values() for sentence in doc]
        self.plain = BM25([terms(s.text) for s in self.sentences])
        self.titled = BM25([terms(s.title) + terms(s.text) for s in self.sentences])
        self.document = BM25([
            terms(title) * 3 + [term for s in sentences for term in terms(s.text)]
            for title, sentences in self.docs.items()
        ])
        self.aliases = {title: phrase(name(title)) for title in self.titles}
        self.sentence_phrases = {s: phrase(s.text) for s in self.sentences}

    def retrieve(self, question, method, budget=6):
        if method not in METHODS or budget < 2:
            raise ValueError("Expected a known retrieval method and budget >= 2")
        query = terms(question)
        if method == "sentence_bm25":
            return sorted(self.sentences, key=dict(zip(self.sentences, self.plain.score(query))).get,
                          reverse=True)[:budget]

        doc_scores = dict(zip(self.titles, self.document.score(query)))
        sentence_scores = dict(zip(self.sentences, self.titled.score(query)))
        ranked = {
            title: sorted(doc, key=lambda s: (sentence_scores[s], -s.offset), reverse=True)
            for title, doc in self.docs.items()
        }
        if method == "document_bm25":
            chosen = sorted(self.titles, key=doc_scores.get, reverse=True)[:2]
            return self.pack(ranked, chosen, budget)

        q_phrase = phrase(question)
        max_doc = max(doc_scores.values(), default=1) or 1
        max_sent = max(sentence_scores.values(), default=1) or 1
        q_terms = set(query)
        prior = {}
        for title in self.titles:
            title_terms = set(terms(name(title)))
            coverage = len(title_terms & q_terms) / max(1, len(title_terms))
            prior[title] = (doc_scores[title] / max_doc
                            + .45 * sentence_scores[ranked[title][0]] / max_sent
                            + .55 * coverage + .8 * (self.aliases[title] in q_phrase))
        if method == "title_bm25" or len(self.titles) < 2:
            return self.pack(ranked, sorted(self.titles, key=prior.get, reverse=True)[:2], budget)

        def link(source, destination):
            alias = self.aliases[destination]
            if alias in q_phrase or len(alias.strip()) < 4:
                return 0, None
            matches = [s for s in ranked[source][:4] if alias in self.sentence_phrases[s]]
            if not matches:
                return 0, None
            sentence = matches[0]
            strength = (.4 + .6 * sentence_scores[sentence] / max_sent) * min(prior[source], 1)
            return strength, sentence

        def pair(first, second):
            strength, connector = max((link(first, second), link(second, first)),
                                      key=lambda candidate: candidate[0])
            if method == "no_links":
                strength, connector = 0, None
            return prior[first] + prior[second] + 1.55 * strength, connector

        first, second = max(combinations(self.titles, 2), key=lambda pair_: pair(*pair_)[0])
        _, connector = pair(first, second)
        chosen = sorted((first, second), key=prior.get, reverse=True)
        if connector:
            ranked[connector.title].remove(connector)
            ranked[connector.title].insert(0, connector)
        return self.pack(ranked, chosen, budget)

    @staticmethod
    def pack(ranked, chosen, budget):
        packet = []
        for offset in range(budget):
            for title in chosen:
                if offset < len(ranked[title]):
                    packet.append(ranked[title][offset])
        return packet[:budget]
