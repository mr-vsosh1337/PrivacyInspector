from typing import List, Tuple

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider

from config import PROTECTED_WORDS, SUPPORTED_EXTS

ENTITIES = None


def add_russian_recognizers(analyzer: AnalyzerEngine) -> None:
    patterns = [
        ("RU_PHONE",
         r"(?<!\d)(?:\+7|8)\s*\(?\d{3}\)?[\s\-]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}(?!\d)",
         0.95,
         "PHONE_NUMBER"),
        ("RU_PASSPORT", r"\b\d{4}\s?\d{6}\b", 0.90, "RUS_PASSPORT"),
        ("RU_INN", r"\b(?:\d{10}|\d{12})\b", 0.85, "INN"),
        ("RU_SNILS", r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b", 0.90, "SNILS"),
        ("RU_OGRN", r"\b\d{13}\b", 0.80, "OGRN"),
        ("RU_OGRNIP", r"\b\d{15}\b", 0.80, "OGRNIP"),
        ("RU_KPP", r"\b\d{9}\b", 0.70, "KPP"),
    ]

    for name, regex, score, entity in patterns:
        recognizer = PatternRecognizer(
            supported_entity=entity,
            patterns=[Pattern(name=name, regex=regex, score=score)],
            supported_language="ru",
        )
        analyzer.registry.add_recognizer(recognizer)


def build_analyzer() -> AnalyzerEngine:
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": "en", "model_name": "en_core_web_lg"},
            {"lang_code": "ru", "model_name": "ru_core_news_lg"},
        ],
    }
    provider = NlpEngineProvider(nlp_configuration=nlp_config)
    nlp_engine = provider.create_engine()

    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en", "ru"])
    add_russian_recognizers(analyzer)
    return analyzer
