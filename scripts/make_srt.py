"""Create Chinese, English, and bilingual SRT files."""

import argparse
import json
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aligned", required=True)
    parser.add_argument("--translations", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--hold", type=float, default=1.5)
    parser.add_argument("--next-gap", type=float, default=0.1)
    return parser.parse_args()


def timestamp(seconds):
    total_ms = max(0, round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(path, cues, line_builder):
    blocks = []
    for index, cue in enumerate(cues, start=1):
        lines = line_builder(index - 1, cue)
        blocks.append(
            f"{index}\n{timestamp(cue['start'])} --> {timestamp(cue['end'])}\n{lines}"
        )
    Path(path).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    cues = json.loads(Path(args.aligned).read_text(encoding="utf-8"))
    translations = json.loads(Path(args.translations).read_text(encoding="utf-8"))

    if len(cues) != len(translations):
        raise SystemExit(f"Cue/translation mismatch: {len(cues)} vs {len(translations)}")
    if not all(isinstance(text, str) and text.strip() for text in translations):
        raise SystemExit("Every translation must be a non-empty string")

    for index, cue in enumerate(cues):
        if index + 1 < len(cues):
            limit = cues[index + 1]["start"] - args.next_gap
        else:
            limit = cue["end"] + args.hold
        cue["end"] = max(cue["end"], min(cue["end"] + args.hold, limit))
        if cue["end"] <= cue["start"]:
            raise SystemExit(f"Invalid cue duration at cue {index + 1}")

    prefix = Path(args.prefix)
    write_srt(f"{prefix}.zh.srt", cues, lambda _, cue: cue["zh"])
    write_srt(f"{prefix}.en.srt", cues, lambda index, _: translations[index])
    write_srt(
        f"{prefix}.bilingual.srt",
        cues,
        lambda index, cue: f"{cue['zh']}\n{translations[index]}",
    )
    print(f"wrote 3 SRT files, {len(cues)} cues each")


if __name__ == "__main__":
    main()
