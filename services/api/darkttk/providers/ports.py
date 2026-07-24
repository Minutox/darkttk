from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GeneratedIdea:
    topic: str
    creative_angle: str
    content_promise: str
    hook: str
    narrative_structure: str
    key_information: str
    call_to_action: str
    visual_suggestion: str
    duration_seconds: int
    target_audience: str
    objective: str


@dataclass(frozen=True)
class GeneratedScript:
    content: str
    style: str


@dataclass(frozen=True)
class CheckedClaim:
    claim: str
    verdict: str
    confidence: int
    evidence: str


class LanguageModelPort(Protocol):
    provider_key: str
    is_mock: bool

    def generate_idea(self, niche: str, topic: str, objective: str) -> GeneratedIdea: ...

    def generate_script(
        self, idea: GeneratedIdea, style: str, duration_seconds: int
    ) -> GeneratedScript: ...


class FactCheckerPort(Protocol):
    provider_key: str
    is_mock: bool

    def check(self, script: str, source_count: int) -> list[CheckedClaim]: ...


@dataclass(frozen=True)
class SynthesizedAudio:
    content: bytes
    mime_type: str
    duration_ms: int
    file_extension: str


class TextToSpeechPort(Protocol):
    provider_key: str
    is_mock: bool

    def synthesize(
        self,
        text: str,
        *,
        voice_id: str,
        language: str,
        speaking_rate: int,
    ) -> SynthesizedAudio: ...
