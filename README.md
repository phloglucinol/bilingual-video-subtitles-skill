# Bilingual Video Subtitles Skill

A Claude Code skill that turns an MP4 and its authoritative Chinese transcript into synchronized Chinese, English, and bilingual subtitles, plus selectable soft-subtitle and burned-in hard-subtitle videos.

一个用于 Claude Code 的双语视频字幕 Skill：输入 MP4 和对应中文文稿，输出对齐后的中文、英文、中英双语字幕，以及软字幕和硬字幕成片。

## 核心原则

当已经有准确文稿时，不让 ASR 重新“猜”字幕内容。

本 Skill 使用 [stable-ts](https://github.com/jianfch/stable-ts) / Whisper 做**强制对齐**：

- 中文文稿是字幕文本的唯一事实来源。
- Whisper 只负责提供时间戳。
- 英文按对齐后的字幕逐条翻译。
- 每个阶段都保留 JSON 和 SRT 中间文件，方便人工修改。

相比直接用 Whisper 转写，这种方式不会把已有的正确文稿替换成带错别字的识别结果，特别适合教学演示、课程录屏、产品演示和已有讲稿的解说视频。

## 功能

- 从 MP4 提取 16 kHz 单声道音频。
- 根据中文标点和长度自动切分字幕。
- 使用 stable-ts 将中文文稿强制对齐到语音。
- 生成逐条英文翻译文件并校验条目数量。
- 生成中文、英文、中英双语三份 SRT。
- 生成包含三条可切换字幕轨的软字幕 MP4，不重新编码原视频。
- 生成烧录中英双语字幕的硬字幕 MP4。
- NVIDIA GPU 可用时自动使用 NVENC，否则使用 `libx264`。
- 校验字幕重叠、时间范围、视频时长和软字幕轨数量。
- 自动抽取首、中、尾检查帧供视觉质检。
- 在交付前检查密码、Token、私人 URL、账号和二维码等敏感信息。
- 默认不覆盖原视频和已有成片。

## 产出文件

以输出前缀 `demo` 为例：

```text
demo_aligned.json          # 中文字幕及对齐时间戳
demo_translations.json     # 与字幕一一对应的英文翻译
demo.zh.srt                # 中文字幕
demo.en.srt                # 英文字幕
demo.bilingual.srt         # 中英双语字幕
demo_软字幕.mp4             # 中文、英文、双语三条可切换字幕轨
demo_硬字幕双语.mp4         # 双语字幕直接烧进画面
demo_检查帧/                # 首、中、尾视觉检查帧
```

## 环境要求

- Linux（脚本本身可跨平台，但当前主要在 Linux 上验证）
- Python 3.11
- [uv](https://docs.astral.sh/uv/)
- FFmpeg / FFprobe
- 中文字体，推荐 `Noto Sans CJK SC`
- 可选：NVIDIA GPU 与 FFmpeg `h264_nvenc` 编码器

Fedora：

```bash
sudo dnf install ffmpeg google-noto-sans-cjk-fonts
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ubuntu/Debian：

```bash
sudo apt install ffmpeg fonts-noto-cjk
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 安装 Skill

### 项目级安装（推荐）

在需要制作字幕的项目根目录执行：

```bash
mkdir -p .claude/skills
git clone https://github.com/phloglucinol/bilingual-video-subtitles-skill.git \
  .claude/skills/bilingual-video-subtitles
```

然后从该项目根目录启动或重新启动 Claude Code：

```bash
claude
```

### 用户级安装

希望所有项目都能使用时：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/phloglucinol/bilingual-video-subtitles-skill.git \
  ~/.claude/skills/bilingual-video-subtitles
```

## 使用方法

在 Claude Code 中调用：

```text
/bilingual-video-subtitles path/to/video.mp4 path/to/transcript.txt demo
```

也可以自然语言描述：

```text
请用这个 MP4 和对应中文文稿生成中英双语字幕，同时输出软字幕和硬字幕视频。
```

Skill 会依次完成：

1. 检查视频流和时长。
2. 提取音频。
3. 强制对齐中文文稿。
4. 逐条翻译英文。
5. 生成三份 SRT。
6. 生成软字幕和硬字幕 MP4。
7. 校验时间轴和字幕轨。
8. 抽帧检查字幕效果及敏感信息。

## 手动运行脚本

如果不通过 Claude Code，也可以单独使用仓库中的脚本。

### 1. 创建环境

```bash
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements.txt
```

### 2. 提取音频

```bash
ffmpeg -y -v error -i video.mp4 -vn -ac 1 -ar 16000 demo_audio.wav
```

### 3. 强制对齐中文文稿

```bash
.venv/bin/python scripts/align_transcript.py \
  --audio demo_audio.wav \
  --transcript transcript.txt \
  --output demo_aligned.json \
  --model small \
  --max-len 28
```

`--max-len` 控制单条中文字幕的最大字数。默认 28；希望字幕更短时可设为 22–24。

### 4. 准备英文翻译

读取 `demo_aligned.json` 中每个对象的 `zh` 字段，按原顺序写成 JSON 字符串数组：

```json
[
  "This is the first English subtitle.",
  "This is the second English subtitle."
]
```

保存为 `demo_translations.json`。数组长度必须和中文字幕条数完全一致。

### 5. 生成 SRT

```bash
.venv/bin/python scripts/make_srt.py \
  --aligned demo_aligned.json \
  --translations demo_translations.json \
  --prefix demo
```

### 6. 生成软字幕和硬字幕视频

```bash
.venv/bin/python scripts/render_video.py \
  --video video.mp4 \
  --prefix demo \
  --font "Noto Sans CJK SC"
```

默认硬字幕参数：

- 字号：14
- 描边：1
- 下边距：18
- NVENC CQ：23

可以使用 `--font-size`、`--margin-v` 和 `--cq` 调整。

### 7. 校验并抽帧

```bash
.venv/bin/python scripts/validate_outputs.py \
  --video video.mp4 \
  --prefix demo \
  --frames-dir demo_检查帧
```

校验内容包括：

- 每条字幕开始、结束时间有效。
- 字幕之间不存在明显重叠。
- 最后一条字幕不超出视频长度。
- 软字幕视频包含三条字幕轨。
- 抽取第一条、中间位置和最后一条字幕的画面。

## 翻译规范

- 每条中文对应一条英文，不合并、不拆分。
- 英文以字幕可读性为优先，避免机械照搬中文语序。
- 数字、单位、课程名、产品名和缩写必须准确。
- 同一术语在整个视频中保持一致。
- 医学、药学、法律等专业内容应核对术语，不能凭空猜测。
- 英文过长时优先精简表达，不要改变时间轴结构。

## 隐私检查

演示录屏经常包含敏感信息。交付前应重点检查：

- 登录页中的明文密码。
- 账号、手机号、邮箱和个人姓名。
- Access Token、API Key、Cookie 和终端环境变量。
- 私有域名、内网地址和后台管理入口。
- 二维码及可用于加入课堂或系统的邀请码。

发现敏感内容时，应从已验收的字幕成片生成一个新的打码版本，不覆盖原文件。静态输入框可以使用固定遮罩或模糊；移动区域需要跟踪遮罩。打码后必须在敏感内容出现的开始、中间和结束时间附近重新抽帧检查。

## 仓库结构

```text
.
├── README.md
├── LICENSE
├── SKILL.md
├── requirements.txt
└── scripts/
    ├── align_transcript.py
    ├── make_srt.py
    ├── render_video.py
    └── validate_outputs.py
```

## 已验证环境

- Fedora Linux
- Python 3.11.13
- uv 0.11.29
- stable-ts 2.19.1
- FFmpeg 8.1.2
- NVIDIA RTX 5070 / `h264_nvenc`
- 1920×1200、约 5.5 分钟中文教学平台演示视频

完整测试结果：73 条字幕，时间范围 5.200–324.860 秒，零重叠，三条软字幕轨正常，NVENC 双语硬字幕渲染正常。

## 限制

- 文稿必须与视频中的实际旁白基本一致；缺句、增句或顺序不同会导致时间轴漂移。
- `small` 模型适合大多数清晰普通话；对齐不准确时可尝试 `medium`，但速度和显存占用更高。
- 英文翻译质量取决于翻译者或调用该 Skill 的模型，脚本本身不调用在线翻译 API。
- 硬字幕需要重新编码视频；软字幕不会重新编码原视频流。
- 当前切句主要面向中文标点，其他语言需要调整 `align_transcript.py` 的切句规则。

## License

[MIT](LICENSE)
