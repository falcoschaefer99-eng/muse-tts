# MUSE TTS Live v2.0

**Free, local text-to-speech + voice cloning for Claude.** Give your AI any voice.

Three engines:
- **Kokoro-82M** — 54 preset voices, 9 languages, ~1s generation
- **IndexTTS-1.5** — Voice cloning, incredible quality (Apple Silicon)
- **Chatterbox OG** — Voice cloning, cross-platform fallback (Windows/Linux)

Runs locally — no cloud APIs, no Docker. All processing on-device, fully private.

**macOS, Windows, and Linux.**

Part of the [MUSE Studio](https://ko-fi.com/thefunkatorium) line by The Funkatorium.

## Quick Start

### 1. Install dependencies

**macOS (Apple Silicon — fastest, best cloning quality):**
```bash
pip install fastmcp mlx_audio
```

**Windows / Linux / Intel Mac:**
```bash
# Preset voices only
pip install fastmcp kokoro soundfile numpy

# Add voice cloning
pip install chatterbox-tts
```

> On Linux, you also need `espeak-ng`: `sudo apt install espeak-ng`

### 2. Add to Claude Desktop

Open Claude Desktop settings and add to your MCP servers:

```json
{
  "mcpServers": {
    "muse-tts-live": {
      "command": "python3",
      "args": ["/path/to/muse-tts/server.py"]
    }
  }
}
```

### 3. Add to Claude Code

```bash
claude mcp add muse-tts-live python3 /path/to/muse-tts/server.py
```

### 4. Talk

Ask Claude to speak! It now has access to `muse_speak`, `muse_list_voices`, and `muse_check`.

## Voice Cloning

Clone any voice from a short reference audio clip.

**Use a bundled voice clone:**
```
muse_speak("To be or not to be", clone="pedro_pascal")
```

**Use your own reference audio:**
```
muse_speak("Hello world", ref_audio="/path/to/my_voice.wav")
```

### Bundled Voice Clones

9 community voice clones included in the `voices/` directory:

| Clone ID | Voice |
|----------|-------|
| `pedro_pascal` | Pedro Pascal |
| `oscar_isaac` | Oscar Isaac |
| `idris_elba` | Idris Elba |
| `jdm` | Jeffrey Dean Morgan |
| `jensen_ackles` | Jensen Ackles |
| `keanu_reeves` | Keanu Reeves |
| `cavill` | Henry Cavill |
| `dicaprio` | Leonardo DiCaprio |
| `hiddleston` | Tom Hiddleston |

### Custom Voice Cloning

To clone any voice, provide a reference audio file:

- **Format**: WAV, 24kHz, mono
- **Length**: 10–30 seconds of clean speech
- **Quality**: Clear audio, minimal background noise

Convert your audio:
```bash
ffmpeg -i input.mp3 -ar 24000 -ac 1 -t 15 reference.wav
```

### Adding Permanent Clones

Drop any `.wav` reference file into the `voices/` directory. It will be automatically detected on server restart and available as `clone="filename"` (without the .wav extension).

## How It Works

MUSE TTS Live auto-detects the best engine for your platform:

| Platform | Kokoro (presets) | Cloning engine |
|----------|-----------------|----------------|
| macOS Apple Silicon (M1–M4) | mlx_audio | **IndexTTS-1.5** (mlx_audio) |
| Windows | kokoro PyTorch | Chatterbox OG (PyTorch) |
| Linux | kokoro PyTorch | Chatterbox OG (PyTorch) |
| Intel Mac | kokoro PyTorch | Chatterbox OG (PyTorch) |

Audio playback is handled natively:
- **macOS**: `afplay`
- **Windows**: PowerShell `SoundPlayer`
- **Linux**: `aplay`, `paplay`, or `ffplay` (whichever is available)

## Configuration

Set defaults via environment variables:

```json
{
  "mcpServers": {
    "muse-tts-live": {
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

## Preset Voices

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
| `muse_speak` | Speak text — preset voice, named clone, or custom ref audio |
| `muse_list_voices` | Browse 54 presets + 9 clones, filter by language or "clone" |
| `muse_check` | Verify engines, platform, and configuration |

## Requirements

- Python 3.10+
- One of: `mlx_audio` (Mac M-series) or `kokoro` + `soundfile` (any platform)
- Optional: `chatterbox-tts` for voice cloning on non-Apple platforms
- ~200MB disk (Kokoro model) + ~1.5GB (IndexTTS-1.5, Apple Silicon) or ~2.5GB (Chatterbox, cross-platform)

## License

MIT + Commons Clause — free for personal use, modification, and redistribution. Cannot be sold as a product or service.

---

Built by [The Funkatorium](https://ko-fi.com/thefunkatorium)
