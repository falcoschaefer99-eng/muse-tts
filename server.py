"""
MUSE TTS — Free Kokoro TTS for Claude

Give Claude a voice. Local, private, fast.

Powered by Kokoro-82M. Runs locally — no cloud APIs, no Docker.
Auto-detects the best engine for your platform:
  - Apple Silicon: mlx_audio (fastest)
  - Windows/Linux: kokoro PyTorch (cross-platform)

Tools:
    muse_speak       - Speak text out loud
    muse_list_voices - Browse all available voices
    muse_check       - Verify TTS is ready

Part of the MUSE Studio line by The Funkatorium.
"""

import os
import sys
import platform
import subprocess
import tempfile

from mcp.server.fastmcp import FastMCP


def log(msg: str):
    """Print to stderr so we don't pollute the MCP JSON-RPC stdout stream."""
    print(msg, file=sys.stderr)

# ============================================
# CONFIGURATION
# ============================================

KOKORO_VOICE = os.getenv("KOKORO_VOICE", "am_fenrir")
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.0"))

# Engine detection: mlx_audio (Apple Silicon) or kokoro (PyTorch cross-platform)
_engine = None

def detect_engine():
    """Auto-detect the best available TTS engine."""
    global _engine
    if _engine is not None:
        return _engine

    # Try mlx_audio first (Apple Silicon, fastest)
    try:
        from mlx_audio.tts.generate import generate_audio
        _engine = "mlx"
        return _engine
    except ImportError:
        pass

    # Fall back to kokoro PyTorch (cross-platform)
    try:
        from kokoro import KPipeline
        _engine = "kokoro"
        return _engine
    except ImportError:
        pass

    _engine = "none"
    return _engine


# All available Kokoro voices
VOICES = {
    "American English (Female)": [
        ("af_alloy", "Alloy"),
        ("af_aoede", "Aoede"),
        ("af_bella", "Bella"),
        ("af_heart", "Heart"),
        ("af_jessica", "Jessica"),
        ("af_kore", "Kore"),
        ("af_nicole", "Nicole"),
        ("af_nova", "Nova"),
        ("af_river", "River"),
        ("af_sarah", "Sarah"),
        ("af_sky", "Sky"),
    ],
    "American English (Male)": [
        ("am_adam", "Adam"),
        ("am_echo", "Echo"),
        ("am_eric", "Eric"),
        ("am_fenrir", "Fenrir"),
        ("am_liam", "Liam"),
        ("am_michael", "Michael"),
        ("am_onyx", "Onyx"),
        ("am_puck", "Puck"),
        ("am_santa", "Santa"),
    ],
    "British English (Female)": [
        ("bf_alice", "Alice"),
        ("bf_emma", "Emma"),
        ("bf_isabella", "Isabella"),
        ("bf_lily", "Lily"),
    ],
    "British English (Male)": [
        ("bm_daniel", "Daniel"),
        ("bm_fable", "Fable"),
        ("bm_george", "George"),
        ("bm_lewis", "Lewis"),
    ],
    "Spanish": [
        ("ef_dora", "Dora"),
        ("em_alex", "Alex"),
        ("em_santa", "Santa"),
    ],
    "French": [
        ("ff_siwis", "Siwis"),
    ],
    "Hindi": [
        ("hf_alpha", "Alpha"),
        ("hf_beta", "Beta"),
        ("hm_omega", "Omega"),
        ("hm_psi", "Psi"),
    ],
    "Italian": [
        ("if_sara", "Sara"),
        ("im_nicola", "Nicola"),
    ],
    "Japanese": [
        ("jf_alpha", "Alpha"),
        ("jf_gongitsune", "Gongitsune"),
        ("jf_nezumi", "Nezumi"),
        ("jf_tebukuro", "Tebukuro"),
        ("jm_kumo", "Kumo"),
    ],
    "Portuguese": [
        ("pf_dora", "Dora"),
        ("pm_alex", "Alex"),
        ("pm_santa", "Santa"),
    ],
    "Mandarin Chinese": [
        ("zf_xiaobei", "Xiaobei"),
        ("zf_xiaoni", "Xiaoni"),
        ("zf_xiaoxiao", "Xiaoxiao"),
        ("zf_xiaoyi", "Xiaoyi"),
        ("zm_yunjian", "Yunjian"),
        ("zm_yunxi", "Yunxi"),
        ("zm_yunxia", "Yunxia"),
        ("zm_yunyang", "Yunyang"),
    ],
}

# Flat lookup for validation
ALL_VOICE_IDS = {vid for group in VOICES.values() for vid, _ in group}

# Language code lookup for kokoro PyTorch engine
LANG_CODES = {
    "a": ["af_", "am_"],
    "b": ["bf_", "bm_"],
    "e": ["ef_", "em_"],
    "f": ["ff_"],
    "h": ["hf_", "hm_"],
    "i": ["if_", "im_"],
    "j": ["jf_", "jm_"],
    "p": ["pf_", "pm_"],
    "z": ["zf_", "zm_"],
}


def get_lang_code(voice_id: str) -> str:
    """Get the language code for a voice ID."""
    for code, prefixes in LANG_CODES.items():
        if any(voice_id.startswith(p) for p in prefixes):
            return code
    return "a"


# ============================================
# AUDIO PLAYBACK (cross-platform)
# ============================================

def play_audio(filepath: str) -> bool:
    """Play a WAV file using the platform's native player."""
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["afplay", filepath], check=True)
        elif system == "Windows":
            # PowerShell can play audio on any Windows install
            subprocess.run(
                ["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"],
                check=True,
            )
        else:
            # Linux — try aplay (ALSA), then paplay (PulseAudio), then ffplay
            for cmd in [["aplay", filepath], ["paplay", filepath], ["ffplay", "-nodisp", "-autoexit", filepath]]:
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    return True
                except FileNotFoundError:
                    continue
            log("MUSE TTS: No audio player found. Install alsa-utils, pulseaudio-utils, or ffmpeg.")
            return False
        return True
    except Exception as e:
        log(f"MUSE TTS playback error: {e}")
        return False


# ============================================
# TTS ENGINE
# ============================================

# Lazy-loaded pipeline for kokoro PyTorch engine
_kokoro_pipelines = {}


def generate_and_play(text: str, voice: str, speed: float) -> bool:
    """Generate speech with the best available engine and play it."""
    engine = detect_engine()

    if engine == "none":
        log("MUSE TTS: No TTS engine found. Install mlx_audio (Mac) or kokoro (any platform).")
        return False

    try:
        if engine == "mlx":
            return _generate_mlx(text, voice, speed)
        else:
            return _generate_kokoro(text, voice, speed)
    except Exception as e:
        log(f"MUSE TTS error: {e}")
        return False


def _generate_mlx(text: str, voice: str, speed: float) -> bool:
    """Generate speech using mlx_audio (Apple Silicon)."""
    from mlx_audio.tts.generate import generate_audio

    generate_audio(
        text=text,
        model_path="prince-canuma/Kokoro-82M",
        voice=voice,
        speed=speed,
        audio_format="wav",
    )
    return play_audio("./audio_000.wav")


def _generate_kokoro(text: str, voice: str, speed: float) -> bool:
    """Generate speech using kokoro PyTorch (cross-platform)."""
    import soundfile as sf
    from kokoro import KPipeline

    lang_code = get_lang_code(voice)

    # Cache pipelines by language code
    if lang_code not in _kokoro_pipelines:
        _kokoro_pipelines[lang_code] = KPipeline(lang_code=lang_code)

    pipeline = _kokoro_pipelines[lang_code]

    # Generate audio chunks and concatenate
    import numpy as np
    audio_chunks = []
    for _, _, audio in pipeline(text, voice=voice, speed=speed):
        audio_chunks.append(audio)

    if not audio_chunks:
        return False

    full_audio = np.concatenate(audio_chunks)

    # Write to temp file and play
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    sf.write(tmp_path, full_audio, 24000)
    result = play_audio(tmp_path)

    # Cleanup
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    return result


# ============================================
# MCP SERVER
# ============================================

mcp = FastMCP("muse-tts")


@mcp.tool()
def muse_speak(text: str, voice: str = "", speed: float = 0) -> str:
    """
    Speak text out loud using Kokoro TTS.

    Generates natural-sounding speech locally on your machine.
    All processing happens on-device — nothing sent to the cloud.

    Args:
        text: The text to speak out loud
        voice: Kokoro voice ID (e.g. "am_onyx", "af_bella"). Use muse_list_voices to see all options.
        speed: Speed multiplier (default 1.0). Range: 0.5 to 2.0. Higher = faster.

    Returns:
        Confirmation message
    """
    voice = voice or KOKORO_VOICE
    speed = speed or KOKORO_SPEED

    if voice not in ALL_VOICE_IDS:
        return f"Unknown voice '{voice}'. Use muse_list_voices to see available voices."

    speed = max(0.5, min(2.0, speed))

    success = generate_and_play(text, voice, speed)

    engine = detect_engine()
    if success:
        return f"Spoke: \"{text[:100]}{'...' if len(text) > 100 else ''}\" (voice: {voice}, speed: {speed}, engine: {engine})"
    else:
        return f"Failed to speak. Run muse_check to diagnose."


@mcp.tool()
def muse_list_voices(language: str = "") -> str:
    """
    List all available Kokoro TTS voices.

    Returns voice IDs grouped by language. Use a voice ID with muse_speak.

    Args:
        language: Optional filter — e.g. "american", "british", "japanese", "spanish"

    Returns:
        Formatted list of available voices
    """
    lines = []
    lines.append(f"Available Kokoro voices (default: {KOKORO_VOICE}):\n")

    for group_name, voices in VOICES.items():
        if language and language.lower() not in group_name.lower():
            continue

        lines.append(f"  {group_name}:")
        for voice_id, display_name in voices:
            marker = " <-- default" if voice_id == KOKORO_VOICE else ""
            lines.append(f"    {voice_id:20s} {display_name}{marker}")
        lines.append("")

    if len(lines) <= 2:
        return f"No voices found matching '{language}'. Try: american, british, spanish, japanese, french, italian, hindi, portuguese, mandarin"

    lines.append(f"Total: {len(ALL_VOICE_IDS)} voices across {len(VOICES)} languages")
    lines.append("\nSet default voice: KOKORO_VOICE=am_onyx")
    lines.append("Set default speed:  KOKORO_SPEED=1.1")

    return "\n".join(lines)


@mcp.tool()
def muse_check() -> dict:
    """
    Check if MUSE TTS is ready to speak.

    Returns status of the TTS engine and platform info.
    """
    engine = detect_engine()
    status = {
        "engine": engine,
        "platform": f"{platform.system()} {platform.machine()}",
        "voice": KOKORO_VOICE,
        "speed": KOKORO_SPEED,
    }

    if engine == "mlx":
        status["status"] = "ready (mlx_audio — Apple Silicon)"
    elif engine == "kokoro":
        status["status"] = "ready (kokoro PyTorch — cross-platform)"
    else:
        status["status"] = "no engine found"
        status["help"] = "Install: pip install mlx_audio (Mac M-series) or pip install kokoro soundfile (any platform)"

    return status


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    engine = detect_engine()
    engine_label = {
        "mlx": "mlx_audio (Apple Silicon)",
        "kokoro": "kokoro PyTorch (cross-platform)",
        "none": "NOT FOUND — install mlx_audio or kokoro",
    }.get(engine, "unknown")

    log("\n" + "=" * 50)
    log("  MUSE TTS — Free Kokoro TTS for Claude")
    log("  By The Funkatorium")
    log("=" * 50)
    log(f"\n  Engine: {engine_label}")
    log(f"  Platform: {platform.system()} {platform.machine()}")
    log(f"  Voice: {KOKORO_VOICE}")
    log(f"  Speed: {KOKORO_SPEED}x")
    log(f"  Voices: {len(ALL_VOICE_IDS)} available")
    log("\n  Tools:")
    log("    muse_speak       — Speak text")
    log("    muse_list_voices — Browse voices")
    log("    muse_check       — System status")
    log("\n" + "=" * 50 + "\n")

    mcp.run()
