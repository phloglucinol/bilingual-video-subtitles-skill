"""Mux selectable subtitles and render a bilingual hard-subtitle video."""

import argparse
import shutil
import subprocess
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--font", default="Noto Sans CJK SC")
    parser.add_argument("--font-size", type=int, default=14)
    parser.add_argument("--margin-v", type=int, default=18)
    parser.add_argument("--cq", type=int, default=23)
    return parser.parse_args()


def run(command, cwd=None):
    print("+", " ".join(str(part) for part in command))
    subprocess.run(command, cwd=cwd, check=True)


def has_encoder(name):
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        check=True,
        capture_output=True,
        text=True,
    )
    return name in result.stdout


def main():
    args = parse_args()
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg is not installed")

    video = Path(args.video).resolve()
    prefix = Path(args.prefix).resolve()
    work_dir = prefix.parent
    stem = prefix.name
    zh = work_dir / f"{stem}.zh.srt"
    en = work_dir / f"{stem}.en.srt"
    bilingual = work_dir / f"{stem}.bilingual.srt"
    for path in (video, zh, en, bilingual):
        if not path.exists():
            raise SystemExit(f"Missing input: {path}")

    soft_output = work_dir / f"{stem}_软字幕.mp4"
    hard_output = work_dir / f"{stem}_硬字幕双语.mp4"
    if soft_output.exists() or hard_output.exists():
        raise SystemExit("Output already exists; choose a new prefix or remove it explicitly")

    run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(video),
            "-i", str(zh), "-i", str(en), "-i", str(bilingual),
            "-map", "0:v", "-map", "0:a", "-map", "1", "-map", "2", "-map", "3",
            "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
            "-metadata:s:s:0", "language=chi", "-metadata:s:s:0", "title=中文",
            "-metadata:s:s:1", "language=eng", "-metadata:s:s:1", "title=English",
            "-metadata:s:s:2", "language=und", "-metadata:s:s:2", "title=中英双语",
            str(soft_output),
        ]
    )

    escaped_subtitle = bilingual.name.replace("'", r"\'").replace(":", r"\:")
    style = (
        f"FontName={args.font},FontSize={args.font_size},Outline=1,"
        f"Shadow=0,MarginV={args.margin_v}"
    )
    video_filter = f"subtitles=filename='{escaped_subtitle}':force_style='{style}'"

    if has_encoder("h264_nvenc"):
        encoder_args = ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", str(args.cq)]
        encoder = "h264_nvenc"
    else:
        encoder_args = ["-c:v", "libx264", "-preset", "medium", "-crf", str(args.cq)]
        encoder = "libx264"

    run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(video),
            "-vf", video_filter, *encoder_args, "-c:a", "copy", str(hard_output),
        ],
        cwd=work_dir,
    )
    print(f"soft subtitles: {soft_output}")
    print(f"hard subtitles: {hard_output}")
    print(f"hard-subtitle encoder: {encoder}")


if __name__ == "__main__":
    main()
