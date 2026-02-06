# MUSE TTS

**Free, local text-to-speech for Claude.** Give your AI a voice.

Powered by [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M). Runs locally — no cloud APIs, no Docker. All processing on-device, fully private.

54 voices. 9 languages. Adjustable speed. **macOS, Windows, and Linux.**

Part of the [MUSE Studio](https://ko-fi.com/thefunkatorium) line by The Funkatorium.

## Quick Start

### 1. Install dependencies

**macOS (Apple Silicon — fastest):**
```bash
pip install fastmcp mlx_audio
```

**Windows / Linux / Intel Mac:**
```bash
pip install fastmcp kokoro soundfile numpy
```

> On Linux, you also need `espeak-ng`: `sudo apt install espeak-ng`

### 2. Add to Claude Desktop

Open Claude Desktop settings and add to your MCP servers:

```json
{
  "mcpServers": {
    "muse-tts": {
      "command": "python3",
      "args": ["/path/to/muse-tts/server.py"]
    }
  }
}
```

### 3. Add to Claude Code

```bash
claude mcp add muse-tts python3 /path/to/muse-tts/server.py
```

### 4. Talk

Ask Claude to speak! It now has access to `muse_speak`, `muse_list_voices`, and `muse_check`.

## How It Works

MUSE TTS auto-detects the best engine for your platform:

| Platform | Engine | Install |
|----------|--------|---------|
| macOS Apple Silicon (M1–M4) | mlx_audio | `pip install mlx_audio` |
| Windows | kokoro PyTorch | `pip install kokoro soundfile numpy` |
| Linux | kokoro PyTorch | `pip install kokoro soundfile numpy` + `apt install espeak-ng` |
| Intel Mac | kokoro PyTorch | `pip install kokoro soundfile numpy` |

Audio playback is handled natively:
- **macOS**: `afplay`
- **Windows**: PowerShell `SoundPlayer`
- **Linux**: `aplay`, `paplay`, or `ffplay` (whichever is available)

## Configuration

Set defaults via environment variables:

```json
{
  "mcpServers": {
    "muse-tts": {
      "command": "python3",
      "args": ["/path/to/muse-tts/server.py"],
      "env": {
        "KOKORO_VOICE": "am_onyx",
        "KOKORO_SPEED": "1.1"
      }
    }
  }
}
```

## Voices

54 voices across 9 languages:

| Language | Female | Male |
|----------|--------|------|
| American English | af_alloy, af_aoede, af_bella, af_heart, af_jessica, af_kore, af_nicole, af_nova, af_river, af_sarah, af_sky | am_adam, am_echo, am_eric, am_fenrir, am_liam, am_michael, am_onyx, am_puck, am_santa |
| British English | bf_alice, bf_emma, bf_isabella, bf_lily | bm_daniel, bm_fable, bm_george, bm_lewis |
| Spanish | ef_dora | em_alex, em_santa |
| French | ff_siwis | — |
| Hindi | hf_alpha, hf_beta | hm_omega, hm_psi |
| Italian | if_sara | im_nicola |
| Japanese | jf_alpha, jf_gongitsune, jf_nezumi, jf_tebukuro | jm_kumo |
| Portuguese | pf_dora | pm_alex, pm_santa |
| Mandarin | zf_xiaobei, zf_xiaoni, zf_xiaoxiao, zf_xiaoyi | zm_yunjian, zm_yunxi, zm_yunxia, zm_yunyang |

Use `muse_list_voices` inside Claude to browse them interactively.

## Tools

| Tool | What it does |
|------|-------------|
| `muse_speak` | Speak text with any voice at any speed (0.5x–2.0x) |
| `muse_list_voices` | Browse all 54 voices, filter by language |
| `muse_check` | Verify engine, platform, and configuration |

## Requirements

- Python 3.10+
- One of: `mlx_audio` (Mac M-series) or `kokoro` + `soundfile` (any platform)
- ~200MB disk space (model downloads on first use)

## License

MIT

---

Built by [The Funkatorium](https://ko-fi.com/thefunkatorium)
