---
name: bilingual-video-subtitles
description: Generate synchronized Chinese, English, and bilingual subtitles from an MP4 plus an existing Chinese transcript. Use for transcript alignment, SRT generation, soft-subtitle muxing, hard-subtitle rendering, translation, timing QA, or privacy checks on demonstration videos.
argument-hint: "<video.mp4> <chinese-transcript.txt> [output-prefix]"
---

# Bilingual Video Subtitles

Turn an MP4 and its authoritative Chinese transcript into:

- `<prefix>.zh.srt`
- `<prefix>.en.srt`
- `<prefix>.bilingual.srt`
- `<prefix>_软字幕.mp4` with Chinese, English, and bilingual selectable tracks
- `<prefix>_硬字幕双语.mp4` with Chinese and English burned into the picture

Prefer forced alignment over free-form ASR whenever a transcript exists. The transcript is the source of truth; ASR supplies timing only.

## Inputs

Identify these before running anything:

1. One MP4 with an audio track.
2. One UTF-8 Chinese transcript matching the spoken narration.
3. An output prefix, normally the video stem.

If several plausible files exist, inspect their names and durations. Ask only when the intended pair cannot be inferred safely.

## Environment

Run from the directory containing the input files. Resolve the absolute path of the directory containing this `SKILL.md` and assign it to `SKILL_DIR`. For a project-level installation it is normally:

```bash
SKILL_DIR="<project-root>/.claude/skills/bilingual-video-subtitles"
```

Do not hard-code a user's home directory. Use a local `.venv`; do not install packages globally:

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r "$SKILL_DIR/requirements.txt"
```

Prerequisites: `ffmpeg`, `ffprobe`, and a Chinese font. Prefer `Noto Sans CJK SC`. Use NVIDIA NVENC when available; otherwise fall back to `libx264`.

## Workflow

### 1. Inspect and extract audio

Probe streams and duration first:

```bash
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_type,codec_name,width,height \
  -of default=noprint_wrappers=1 "<video.mp4>"
```

Extract 16 kHz mono WAV:

```bash
ffmpeg -y -v error -i "<video.mp4>" -vn -ac 1 -ar 16000 "<prefix>_audio.wav"
```

### 2. Force-align the authoritative transcript

```bash
.venv/bin/python "$SKILL_DIR/scripts/align_transcript.py" \
  --audio "<prefix>_audio.wav" \
  --transcript "<transcript.txt>" \
  --output "<prefix>_aligned.json" \
  --model small \
  --max-len 28
```

Use `small` by default. Use `medium` only if spot checks show poor timing. The alignment output must report zero overlaps and should span nearly all narrated audio.

### 3. Translate cue by cue

Read `<prefix>_aligned.json`. Translate every `zh` value into concise, natural English and write a UTF-8 JSON array to `<prefix>_translations.json`.

Translation requirements:

- Preserve cue order exactly.
- Produce exactly one English string per Chinese cue.
- Keep terminology consistent across the whole video.
- Translate meaning, not Chinese syntax.
- Prefer concise subtitle phrasing that can be read during the cue.
- Preserve numbers, units, product names, course names, and abbreviations accurately.
- For technical content, verify domain terms rather than guessing.
- Do not merge or split cues at this stage.

Validate counts before continuing:

```bash
.venv/bin/python -c 'import json,sys; a=json.load(open(sys.argv[1])); t=json.load(open(sys.argv[2])); assert len(a)==len(t), (len(a),len(t)); print(len(a), "translations OK")' \
  "<prefix>_aligned.json" "<prefix>_translations.json"
```

### 4. Generate Chinese, English, and bilingual SRT

```bash
.venv/bin/python "$SKILL_DIR/scripts/make_srt.py" \
  --aligned "<prefix>_aligned.json" \
  --translations "<prefix>_translations.json" \
  --prefix "<prefix>"
```

### 5. Render both delivery formats

```bash
.venv/bin/python "$SKILL_DIR/scripts/render_video.py" \
  --video "<video.mp4>" \
  --prefix "<prefix>" \
  --font "Noto Sans CJK SC"
```

This creates a stream-copied soft-subtitle MP4 and an NVENC-rendered hard-subtitle MP4 when NVENC is available.

### 6. Validate and visually inspect

```bash
.venv/bin/python "$SKILL_DIR/scripts/validate_outputs.py" \
  --video "<video.mp4>" \
  --prefix "<prefix>" \
  --frames-dir "<prefix>_检查帧"
```

Then use the image reader on the first, middle, and final extracted frames. Confirm:

- Chinese and English are visible and not clipped.
- Subtitles do not cover essential UI controls or labels.
- Font size and outline remain legible over light and dark areas.
- Early and late cues match the narration.
- The final subtitle does not extend beyond the video.
- Soft-subtitle output contains three subtitle tracks.

### 7. Privacy review before delivery

Inspect frames from login pages, forms, dashboards, browser chrome, and terminal windows. Look for passwords, access tokens, private URLs, personal details, QR codes, and account identifiers.

If sensitive data is visible, do not overwrite the accepted subtitled video. Create a new redacted derivative and re-run visual checks around the full visibility interval. Use a fixed opaque cover or blur for a static field; use tracked masking only when the sensitive region moves.

## Quality Rules

- Never replace known transcript text with imperfect ASR text.
- Do not silently continue after cue/translation count mismatches.
- Do not overwrite source video or accepted outputs.
- Keep intermediate JSON and SRT files so timings and translations remain editable.
- Keep Chinese and English on separate lines in bilingual SRT.
- For 1920-wide video, start with font size 14 in libass style; adjust only after screenshot inspection.
- Report generated paths, cue count, alignment span, video duration, encoder used, and any residual concerns.

## Troubleshooting

- CUDA/Triton warnings during alignment can be harmless if alignment completes and reports timings.
- If alignment drifts, verify that the transcript actually matches the audio, then try `--model medium`.
- If a cue is too long, lower `--max-len` to 22-24 and regenerate alignment.
- If hard subtitles show boxes, install/use `Noto Sans CJK SC` and rerender.
- If `h264_nvenc` is unavailable, `render_video.py` automatically uses `libx264`.
- If the video contains no audio stream, stop and report it; forced alignment cannot proceed.
