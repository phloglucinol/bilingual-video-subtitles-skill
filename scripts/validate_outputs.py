"""Validate subtitle timing/tracks and extract hard-subtitle review frames."""

import argparse
import json
import re
import subprocess
from pathlib import Path


TIME_RE = re.compile(
    r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}),(?P<ms>\d{3})"
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--frames-dir", required=True)
    return parser.parse_args()


def run(command):
    subprocess.run(command, check=True)


def probe(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=index,codec_type,codec_name:stream_tags=language,title",
            "-of", "json", str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def to_seconds(value):
    match = TIME_RE.fullmatch(value)
    if not match:
        raise ValueError(f"Bad SRT timestamp: {value}")
    return (
        int(match["h"]) * 3600
        + int(match["m"]) * 60
        + int(match["s"])
        + int(match["ms"]) / 1000
    )


def parse_srt(path):
    text = Path(path).read_text(encoding="utf-8-sig")
    times = re.findall(
        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})",
        text,
    )
    if not times:
        raise SystemExit(f"No cues found in {path}")
    return [(to_seconds(start), to_seconds(end)) for start, end in times]


def main():
    args = parse_args()
    video = Path(args.video).resolve()
    prefix = Path(args.prefix).resolve()
    hard = prefix.parent / f"{prefix.name}_硬字幕双语.mp4"
    soft = prefix.parent / f"{prefix.name}_软字幕.mp4"
    bilingual = prefix.parent / f"{prefix.name}.bilingual.srt"

    for path in (video, hard, soft, bilingual):
        if not path.exists():
            raise SystemExit(f"Missing output: {path}")

    source_info = probe(video)
    duration = float(source_info["format"]["duration"])
    cues = parse_srt(bilingual)
    for index, (start, end) in enumerate(cues, start=1):
        if start < 0 or end <= start:
            raise SystemExit(f"Invalid cue {index}: {start} -> {end}")
        if index > 1 and start < cues[index - 2][1] - 0.05:
            raise SystemExit(f"Overlapping cue {index}")
    if cues[-1][1] > duration + 0.25:
        raise SystemExit(f"Last cue exceeds video: {cues[-1][1]:.3f} > {duration:.3f}")

    soft_info = probe(soft)
    subtitle_streams = [
        stream for stream in soft_info["streams"] if stream.get("codec_type") == "subtitle"
    ]
    if len(subtitle_streams) != 3:
        raise SystemExit(f"Expected 3 subtitle tracks, found {len(subtitle_streams)}")

    frames_dir = Path(args.frames_dir).resolve()
    frames_dir.mkdir(parents=True, exist_ok=True)
    first_sample = min(cues[0][0] + 0.5, cues[0][1] - 0.1)
    middle_cue = cues[len(cues) // 2]
    middle_sample = (middle_cue[0] + middle_cue[1]) / 2
    last_sample = (cues[-1][0] + cues[-1][1]) / 2
    sample_times = [first_sample, middle_sample, last_sample]
    for label, seconds in zip(("first", "middle", "last"), sample_times):
        output = frames_dir / f"{label}_{seconds:.1f}s.png"
        run([
            "ffmpeg", "-y", "-v", "error", "-ss", f"{seconds:.3f}",
            "-i", str(hard), "-frames:v", "1", str(output),
        ])

    print(f"video duration: {duration:.3f}s")
    print(f"subtitle cues: {len(cues)}")
    print(f"subtitle span: {cues[0][0]:.3f}s -> {cues[-1][1]:.3f}s")
    print("soft subtitle tracks: 3")
    print(f"review frames: {frames_dir}")


if __name__ == "__main__":
    main()
