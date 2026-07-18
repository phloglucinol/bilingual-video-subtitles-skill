"""Force-align an authoritative Chinese transcript to an audio file."""

import argparse
import json
import re
from pathlib import Path

import stable_whisper


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="small")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--max-len", type=int, default=28)
    return parser.parse_args()


def clean_transcript(raw):
    return re.sub(r'[“”"\s]+', "", raw)


def split_long(sentence, max_len):
    if len(sentence) <= max_len:
        return [sentence]

    pieces = [piece for piece in re.split(r"(?<=[，、：])", sentence) if piece]
    combined = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) > max_len:
            combined.append(current)
            current = piece
        else:
            current += piece
    if current:
        combined.append(current)

    result = []
    hard_limit = max_len + 8
    for piece in combined:
        while len(piece) > hard_limit:
            result.append(piece[:max_len])
            piece = piece[max_len:]
        if piece:
            result.append(piece)
    return result


def split_sentences(text, max_len):
    sentences = []
    for sentence in re.split(r"(?<=[。？！；])", text):
        if sentence:
            sentences.extend(split_long(sentence, max_len))
    return sentences


def main():
    args = parse_args()
    raw = Path(args.transcript).read_text(encoding="utf-8")
    text = clean_transcript(raw)
    sentences = split_sentences(text, args.max_len)
    if not sentences:
        raise SystemExit("Transcript is empty after normalization")

    align_text = "".join(sentences)
    print(f"{len(sentences)} subtitle cues, {len(align_text)} chars")

    model = stable_whisper.load_model(args.model)
    result = model.align(args.audio, align_text, language=args.language)
    words = [(word.word.strip(), word.start, word.end) for word in result.all_words()]
    words = [word for word in words if word[0]]
    print(f"aligned {len(words)} tokens")

    cues = []
    word_index = 0
    consumed = ""
    for sentence in sentences:
        start = None
        end = None
        target = len(consumed) + len(sentence)
        while word_index < len(words) and len(consumed) < target:
            word, word_start, word_end = words[word_index]
            if start is None:
                start = word_start
            consumed += word
            end = word_end
            word_index += 1
        if start is None or end is None:
            raise RuntimeError(f"Alignment ended before cue: {sentence}")
        cues.append({"zh": sentence, "start": round(start, 3), "end": round(end, 3)})

    if word_index != len(words):
        raise RuntimeError(f"Alignment mismatch: consumed {word_index} of {len(words)} tokens")

    overlaps = [
        index
        for index in range(1, len(cues))
        if cues[index]["start"] < cues[index - 1]["end"] - 0.05
    ]
    if overlaps:
        raise RuntimeError(f"Alignment contains {len(overlaps)} overlapping cues")

    Path(args.output).write_text(
        json.dumps(cues, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"span: {cues[0]['start']:.1f}s -> {cues[-1]['end']:.1f}s, overlaps: 0")
    for cue in cues[:5]:
        print(f"  {cue['start']:7.2f} - {cue['end']:7.2f}  {cue['zh']}")


if __name__ == "__main__":
    main()
