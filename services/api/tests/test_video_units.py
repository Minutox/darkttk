from darkttk.captions import export_srt, export_vtt, generate_cues
from darkttk.providers.mock import MockTextToSpeech


def test_caption_generation_is_monotonic_and_exportable():
    cues = generate_cues("Uma legenda curta para validar a linha do tempo.", 5_000, 3)
    assert cues
    assert cues[0].start_ms == 0
    assert cues[-1].end_ms == 5_000
    assert all(cue.end_ms > cue.start_ms for cue in cues)
    assert "-->" in export_srt(cues)
    assert export_vtt(cues).startswith("WEBVTT")


def test_mock_tts_is_explicit_and_returns_valid_wav_header():
    provider = MockTextToSpeech()
    audio = provider.synthesize(
        "Narração local de desenvolvimento.",
        voice_id="mock-neutral-ptbr",
        language="pt-BR",
        speaking_rate=100,
    )
    assert provider.is_mock is True
    assert audio.content.startswith(b"RIFF")
    assert audio.content[8:12] == b"WAVE"
    assert audio.duration_ms >= 1_000
