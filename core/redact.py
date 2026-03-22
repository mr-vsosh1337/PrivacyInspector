import re
from typing import List

from presidio_analyzer import AnalyzerEngine, RecognizerResult

from config import REDACTION_TOKEN
from .analyzer import ENTITIES, PROTECTED_WORDS


def exclude_exact_matches(text: str, results: List[RecognizerResult], excluded_texts: set[str]) -> List[
    RecognizerResult]:
    if not excluded_texts:
        return results

    def norm(s: str) -> str:
        return re.sub(r"\s+", " ", s).strip()

    excluded_norm = {norm(x) for x in excluded_texts}

    clean = []
    for r in results:
        span = norm(text[r.start:r.end])
        if span in excluded_norm:
            continue
        clean.append(r)
    return clean


def filter_label_spans(text: str, results: List[RecognizerResult]) -> List[RecognizerResult]:
    clean: List[RecognizerResult] = []
    for r in results:
        span_text = re.sub(r"\s+", " ", text[r.start:r.end]).lower().strip(" \t\r\n:;,.()[]{}\"'")
        if span_text in PROTECTED_WORDS:
            continue
        clean.append(r)
    return clean


def merge_results(results: List[RecognizerResult]) -> List[RecognizerResult]:
    if not results:
        return []
    results = sorted(results, key=lambda r: (r.start, -(r.end - r.start), -r.score))
    merged: List[RecognizerResult] = []

    for r in results:
        if not merged:
            merged.append(r)
            continue

        last = merged[-1]
        if r.start <= last.end:
            last_len = last.end - last.start
            r_len = r.end - r.start
            if (r.end > last.end) or (r_len > last_len) or (r.score > last.score + 0.05):
                merged[-1] = RecognizerResult(
                    entity_type=last.entity_type if last.score >= r.score else r.entity_type,
                    start=min(last.start, r.start),
                    end=max(last.end, r.end),
                    score=max(last.score, r.score),
                )
        else:
            merged.append(r)

    return merged


def analyze_multilang(analyzer: AnalyzerEngine, text: str) -> List[RecognizerResult]:
    if not text or not text.strip():
        return []
    results_ru = analyzer.analyze(text=text, language="ru", entities=ENTITIES)

    merged = merge_results(results_ru)
    return merged


def get_redaction_results(
        analyzer: AnalyzerEngine,
        text: str,
        excluded_texts: set[str] | None = None,
) -> List[RecognizerResult]:
    results = analyze_multilang(analyzer, text)
    if not results:
        return []

    results = filter_label_spans(text, results)

    if excluded_texts:
        results = exclude_exact_matches(text, results, excluded_texts)

    return results


def mask_text(text: str, token: str = REDACTION_TOKEN) -> str:
    if not text:
        return text
    return token or REDACTION_TOKEN


def redact_text(
        analyzer: AnalyzerEngine,
        text: str,
        token: str = REDACTION_TOKEN,
        excluded_texts: set[str] | None = None,
) -> str:
    results = get_redaction_results(analyzer, text, excluded_texts)
    if not results:
        return text

    parts = []
    cursor = 0
    for result in results:
        parts.append(text[cursor:result.start])
        parts.append(mask_text(text[result.start:result.end], token))
        cursor = result.end
    parts.append(text[cursor:])
    return "".join(parts)
