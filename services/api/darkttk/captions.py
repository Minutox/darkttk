from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedCue:
    sequence: int
    start_ms: int
    end_ms: int
    text: str
    highlights: list[str]


def generate_cues(text: str, duration_ms: int, words_per_cue: int = 5) -> list[GeneratedCue]:
    words = text.replace("\n", " ").split()
    if not words:
        return []
    chunks = [words[index : index + words_per_cue] for index in range(0, len(words), words_per_cue)]
    slot = duration_ms / len(chunks)
    cues: list[GeneratedCue] = []
    for index, chunk in enumerate(chunks):
        start = round(index * slot)
        end = round((index + 1) * slot)
        highlights = [word.strip(".,!?;:") for word in chunk if len(word.strip(".,!?;:")) >= 7][:2]
        cues.append(
            GeneratedCue(
                sequence=index + 1,
                start_ms=start,
                end_ms=max(start + 250, end),
                text=" ".join(chunk),
                highlights=highlights,
            )
        )
    return cues


def timestamp_srt(milliseconds: int) -> str:
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1_000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def timestamp_vtt(milliseconds: int) -> str:
    return timestamp_srt(milliseconds).replace(",", ".")


def export_srt(cues: list[GeneratedCue]) -> str:
    return "\n\n".join(
        f"{cue.sequence}\n{timestamp_srt(cue.start_ms)} --> {timestamp_srt(cue.end_ms)}\n{cue.text}"
        for cue in cues
    ) + "\n"


def export_vtt(cues: list[GeneratedCue]) -> str:
    body = "\n\n".join(
        f"{timestamp_vtt(cue.start_ms)} --> {timestamp_vtt(cue.end_ms)}\n{cue.text}"
        for cue in cues
    )
    return f"WEBVTT\n\n{body}\n"
