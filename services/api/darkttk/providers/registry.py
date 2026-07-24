from .mock import MockFactChecker, MockLanguageModel, MockTextToSpeech
from .ports import FactCheckerPort, LanguageModelPort, TextToSpeechPort


def language_model() -> LanguageModelPort:
    return MockLanguageModel()


def fact_checker() -> FactCheckerPort:
    return MockFactChecker()


def text_to_speech() -> TextToSpeechPort:
    return MockTextToSpeech()
