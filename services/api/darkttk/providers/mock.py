import re
import io
import wave

from .ports import CheckedClaim, GeneratedIdea, GeneratedScript, SynthesizedAudio


class MockLanguageModel:
    provider_key = "mock-local-v1"
    is_mock = True

    def generate_idea(self, niche: str, topic: str, objective: str) -> GeneratedIdea:
        clean_topic = topic.strip()
        return GeneratedIdea(
            topic=clean_topic,
            creative_angle=f"Explicar {clean_topic.lower()} por meio de uma pergunta visual e concreta.",
            content_promise="Entregar uma explicação clara em menos de um minuto, sem exageros.",
            hook=f"Você já percebeu isto sobre {clean_topic.lower()}?",
            narrative_structure="gancho → contexto → explicação → exemplo → conclusão",
            key_information=f"O conteúdo deve apresentar o princípio central de {clean_topic} com fonte verificável.",
            call_to_action="Salve para consultar depois e compartilhe com alguém curioso.",
            visual_suggestion=f"Planos curtos, diagramas simples e demonstrações relacionadas a {niche}.",
            duration_seconds=45,
            target_audience=f"Pessoas interessadas em {niche.lower()}, sem conhecimento técnico prévio.",
            objective=objective,
        )

    def generate_script(
        self, idea: GeneratedIdea, style: str, duration_seconds: int
    ) -> GeneratedScript:
        content = (
            f"{idea.hook}\n\n"
            f"{idea.content_promise}\n\n"
            f"Primeiro, observe o contexto: {idea.key_information}\n\n"
            "A explicação precisa ser confirmada por fontes confiáveis antes da publicação. "
            "Use um exemplo visual simples, varie o estímulo e mantenha frases curtas.\n\n"
            f"{idea.call_to_action}"
        )
        return GeneratedScript(content=content, style=style)


class MockFactChecker:
    provider_key = "mock-fact-check-v1"
    is_mock = True

    def check(self, script: str, source_count: int) -> list[CheckedClaim]:
        sentences = [
            item.strip()
            for item in re.split(r"(?<=[.!?])\s+", script.replace("\n", " "))
            if len(item.strip()) >= 24
        ]
        claims = [
            sentence
            for sentence in sentences
            if any(char.isdigit() for char in sentence)
            or any(
                marker in sentence.lower()
                for marker in ("é ", "são ", "causa", "aumenta", "reduz", "primeiro")
            )
        ][:8]
        if not claims:
            return []
        verdict = "needs_review" if source_count == 0 else "supported_by_user_source"
        confidence = 20 if source_count == 0 else 65
        evidence = (
            "Nenhuma fonte foi fornecida; revisão humana obrigatória."
            if source_count == 0
            else "Há fonte fornecida pelo usuário, mas o adaptador mock não valida seu conteúdo."
        )
        return [
            CheckedClaim(
                claim=claim,
                verdict=verdict,
                confidence=confidence,
                evidence=evidence,
            )
            for claim in claims
        ]


class MockTextToSpeech:
    provider_key = "mock-tts-v1"
    is_mock = True

    def synthesize(
        self,
        text: str,
        *,
        voice_id: str,
        language: str,
        speaking_rate: int,
    ) -> SynthesizedAudio:
        words = max(1, len(text.split()))
        words_per_second = max(1.4, 2.5 * speaking_rate / 100)
        duration_ms = min(180_000, max(1_000, round(words / words_per_second * 1000)))
        sample_rate = 16_000
        frame_count = sample_rate * duration_ms // 1000
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            chunk = b"\x00\x00" * min(sample_rate, frame_count)
            remaining = frame_count
            while remaining:
                frames = min(remaining, sample_rate)
                wav.writeframes(chunk[: frames * 2])
                remaining -= frames
        return SynthesizedAudio(
            content=buffer.getvalue(),
            mime_type="audio/wav",
            duration_ms=duration_ms,
            file_extension=".wav",
        )
