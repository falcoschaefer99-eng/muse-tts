"""
MUSE TTS — Free Kokoro TTS for Claude

Give Claude a voice. Local, private, fast.

Powered by Kokoro-82M via mlx_audio (Apple Silicon native).
No cloud API, no Docker, no GPU drivers. Just works.

Tools:
    muse_speak       - Speak text out loud
    muse_list_voices - Browse all available voices
    muse_check       - Verify TTS is ready

Part of the MUSE Studio line by The Funkatorium.
"""

import os
import subprocess

from mcp.server.fastmcp import FastMCP

# ============================================
# CONFIGURATION
# ============================================

KOKORO_MODEL = "prince-canuma/Kokoro-82M"
KOKORO_VOICE = os.getenv("KOKORO_VOICE", "am_fenrir")
KOKORO_SPEED = float(os.getenv("KOKORO_SPEED", "1.0"))

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


# ============================================
# TTS ENGINE
# ============================================

def generate_and_play(text: str, voice: str, speed: float) -> bool:
    """Generate speech with Kokoro and play it."""
    from mlx_audio.tts.generate import generate_audio

    try:
        generate_audio(
            text=text,
            model_path=KOKORO_MODEL,
            voice=voice,
            speed=speed,
            audio_format="wav",
        )
        subprocess.run(["afplay", "./audio_000.wav"], check=True)
        return True
    except Exception as e:
        print(f"MUSE TTS error: {e}")
        return False


# ============================================
# MCP SERVER
# ============================================

mcp = FastMCP("muse-tts")


@mcp.tool()
def muse_speak(text: str, voice: str = "", speed: float = 0) -> str:
    """
    Speak text out loud using Kokoro TTS.

    Generates natural-sounding speech locally on your Mac.
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

    if success:
        return f"Spoke: \"{text[:100]}{'...' if len(text) > 100 else ''}\" (voice: {voice}, speed: {speed})"
    else:
        return f"Failed to speak. Check that mlx_audio is installed."


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

    Returns status of the Kokoro TTS engine.
    """
    status = {"kokoro": "unknown", "voice": KOKORO_VOICE, "speed": KOKORO_SPEED}

    try:
        from mlx_audio.tts.generate import generate_audio
        status["kokoro"] = "ready"
    except ImportError:
        status["kokoro"] = "not installed — run: pip install mlx_audio"
    except Exception as e:
        status["kokoro"] = f"error: {e}"

    return status


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    print("\n" + "=" * 45)
    print("  MUSE TTS — Free Kokoro TTS for Claude")
    print("  By The Funkatorium")
    print("=" * 45)
    print(f"\n  Voice: {KOKORO_VOICE}")
    print(f"  Speed: {KOKORO_SPEED}x")
    print(f"  Voices: {len(ALL_VOICE_IDS)} available")
    print("\n  Tools:")
    print("    muse_speak       — Speak text")
    print("    muse_list_voices — Browse voices")
    print("    muse_check       — System status")
    print("\n" + "=" * 45 + "\n")

    mcp.run()
