"""
MUSE TTS Live v2.0 — Voice Synthesis + Cloning for Claude

Give Claude a voice — preset or cloned. Local, private, fast.

Engines:
  - Kokoro-82M: 54 preset voices, ~1s generation
  - IndexTTS-1.5: Voice cloning, incredible quality (Apple Silicon via mlx_audio)
  - Chatterbox OG: Voice cloning, cross-platform fallback (Windows/Linux via PyTorch)

Auto-detects the best platform backend:
  - Apple Silicon: IndexTTS-1.5 for cloning, Kokoro via mlx_audio for presets
  - Windows/Linux: Chatterbox OG for cloning, Kokoro via PyTorch for presets

Tools:
    muse_speak       - Speak text (preset or cloned voice)
    muse_list_voices - Browse all available voices + clones
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

# Voice clone registry — populated at startup by scanning voices/ directory
CLONE_VOICES = {}

# Display names for bundled clones
CLONE_DISPLAY_NAMES = {
    "pedro_pascal": "Pedro Pascal",
    "oscar_isaac": "Oscar Isaac",
    "idris_elba": "Idris Elba",
    "jdm": "Jeffrey Dean Morgan",
    "jensen_ackles": "Jensen Ackles",
    "keanu_reeves": "Keanu Reeves",
    "cavill": "Henry Cavill",
    "dicaprio": "Leonardo DiCaprio",
    "hiddleston": "Tom Hiddleston",
}


def scan_voices_dir():
    """Scan voices/ directory for bundled reference WAVs."""
    voices_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voices")
    if not os.path.isdir(voices_dir):
        return
    for f in sorted(os.listdir(voices_dir)):
        if f.endswith(".wav"):
            name = f[:-4]
            CLONE_VOICES[name] = os.path.join(voices_dir, f)


# Scan on import
scan_voices_dir()


# ============================================
# ENGINE DETECTION
# ============================================

_engine = None
_clone_engine = None


def detect_engine():
    """Auto-detect the best available TTS engine for Kokoro presets."""
    global _engine
    if _engine is not None:
        return _engine

    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        try:
            from mlx_audio.tts.generate import generate_audio
            _engine = "mlx"
            return _engine
        except ImportError:
            pass

        try:
            from kokoro import KPipeline
            _engine = "kokoro"
            return _engine
        except ImportError:
            pass

        _engine = "none"
        return _engine
    finally:
        sys.stdout = old_stdout


def detect_clone_engine():
    """Check which voice cloning engine is available.
    Returns: 'indextts' (Apple Silicon), 'chatterbox' (Windows/Linux), or 'none'."""
    global _clone_engine
    if _clone_engine is not None:
        return _clone_engine

    # Apple Silicon: IndexTTS-1.5 via mlx_audio (best quality)
    if detect_engine() == "mlx":
        _clone_engine = "indextts"
        return _clone_engine

    # Windows/Linux: Chatterbox OG via PyTorch (cross-platform fallback)
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        try:
            from chatterbox.tts import ChatterboxTTS
            _clone_engine = "chatterbox"
            return _clone_engine
        except ImportError:
            pass
    finally:
        sys.stdout = old_stdout

    _clone_engine = "none"
    return _clone_engine


# ============================================
# KOKORO VOICES
# ============================================

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
            subprocess.run(
                ["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"],
                check=True,
            )
        else:
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
# TTS ENGINES
# ============================================

_kokoro_pipelines = {}


def _play_mlx_output(output_dir: str) -> bool:
    """Play audio from mlx_audio generation, handling multi-chunk concatenation and cleanup."""
    import glob as globmod
    import wave

    wav_files = sorted(globmod.glob(os.path.join(output_dir, "audio_*.wav")))

    if not wav_files:
        log(f"MUSE TTS: no wav files found in {output_dir}")
        return False

    if len(wav_files) == 1:
        result = play_audio(wav_files[0])
    else:
        log(f"MUSE TTS: concatenating {len(wav_files)} audio chunks")
        combined_path = os.path.join(output_dir, "combined.wav")
        try:
            with wave.open(wav_files[0], "rb") as first:
                params = first.getparams()
            with wave.open(combined_path, "wb") as out:
                out.setparams(params)
                for wav_file in wav_files:
                    with wave.open(wav_file, "rb") as chunk:
                        out.writeframes(chunk.readframes(chunk.getnframes()))
            result = play_audio(combined_path)
        except Exception as e:
            log(f"MUSE TTS: concatenation failed: {e}, playing first chunk only")
            result = play_audio(wav_files[0])

    # Cleanup
    for f in globmod.glob(os.path.join(output_dir, "*.wav")):
        try:
            os.unlink(f)
        except OSError:
            pass
    try:
        os.rmdir(output_dir)
    except OSError:
        pass

    return result


def _generate_mlx(text: str, voice: str, speed: float) -> bool:
    """Generate Kokoro speech using mlx_audio (Apple Silicon)."""
    from mlx_audio.tts.generate import generate_audio

    output_dir = tempfile.mkdtemp(prefix="muse_tts_")
    old_cwd = os.getcwd()
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        os.chdir(output_dir)
        generate_audio(
            text=text,
            model="prince-canuma/Kokoro-82M",
            voice=voice,
            speed=speed,
            audio_format="wav",
        )
    finally:
        sys.stdout = old_stdout
        os.chdir(old_cwd)

    return _play_mlx_output(output_dir)


def _generate_indextts_mlx(text: str, ref_audio: str) -> bool:
    """Generate cloned speech using IndexTTS-1.5 via mlx_audio (Apple Silicon)."""
    from mlx_audio.tts.generate import generate_audio

    output_dir = tempfile.mkdtemp(prefix="muse_tts_clone_")
    old_cwd = os.getcwd()
    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        os.chdir(output_dir)
        generate_audio(
            text=text,
            model="mlx-community/IndexTTS-1.5",
            ref_audio=ref_audio,
            audio_format="wav",
            max_tokens=5000,
        )
    finally:
        sys.stdout = old_stdout
        os.chdir(old_cwd)

    return _play_mlx_output(output_dir)


def _generate_kokoro(text: str, voice: str, speed: float) -> bool:
    """Generate Kokoro speech using PyTorch (cross-platform)."""
    import soundfile as sf
    from kokoro import KPipeline

    lang_code = get_lang_code(voice)

    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        if lang_code not in _kokoro_pipelines:
            _kokoro_pipelines[lang_code] = KPipeline(lang_code=lang_code)

        pipeline = _kokoro_pipelines[lang_code]

        import numpy as np
        audio_chunks = []
        for _, _, audio in pipeline(text, voice=voice, speed=speed):
            audio_chunks.append(audio)
    finally:
        sys.stdout = old_stdout

    if not audio_chunks:
        return False

    full_audio = np.concatenate(audio_chunks)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    sf.write(tmp_path, full_audio, 24000)
    result = play_audio(tmp_path)

    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    return result


def _generate_chatterbox_pytorch(text: str, ref_audio: str) -> bool:
    """Generate cloned speech using Chatterbox OG via PyTorch (cross-platform fallback)."""
    import torch
    import torchaudio
    from chatterbox.tts import ChatterboxTTS

    old_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = ChatterboxTTS.from_pretrained(device=device)
        wav = model.generate(text, audio_prompt_path=ref_audio)
    finally:
        sys.stdout = old_stdout

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()

    torchaudio.save(tmp_path, wav, model.sr)
    result = play_audio(tmp_path)

    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    return result


# ============================================
# GENERATION ROUTING
# ============================================

def generate_and_play(text: str, voice: str, speed: float) -> str:
    """Generate Kokoro preset speech and play it.
    Returns empty string on success, error message on failure."""
    engine = detect_engine()

    if engine == "none":
        return "No TTS engine found. Install mlx_audio (Mac) or kokoro (any platform)."

    try:
        if engine == "mlx":
            ok = _generate_mlx(text, voice, speed)
        else:
            ok = _generate_kokoro(text, voice, speed)
        return "" if ok else "Generation or playback failed — check server stderr logs."
    except Exception as e:
        log(f"MUSE TTS error: {e}")
        return f"Error: {e}"


def generate_clone_and_play(text: str, ref_audio: str) -> tuple[str, str]:
    """Generate cloned speech and play it.
    Returns (error, engine_name) — error is empty string on success."""
    clone_eng = detect_clone_engine()

    if clone_eng == "none":
        return ("Voice cloning not available. Install mlx_audio (Mac) or chatterbox-tts (any platform).", "")

    if not os.path.isfile(ref_audio):
        return (f"Reference audio not found: {ref_audio}", "")

    try:
        if clone_eng == "indextts":
            ok = _generate_indextts_mlx(text, ref_audio)
            engine_name = "IndexTTS-1.5"
        else:
            ok = _generate_chatterbox_pytorch(text, ref_audio)
            engine_name = "Chatterbox"
        if ok:
            return ("", engine_name)
        return ("Clone generation or playback failed — check server stderr logs.", "")
    except Exception as e:
        log(f"MUSE TTS clone error: {e}")
        return (f"Error: {e}", "")


# ============================================
# MCP SERVER
# ============================================

mcp = FastMCP("muse-tts-live")


@mcp.tool()
def muse_speak(text: str, voice: str = "", clone: str = "", ref_audio: str = "", speed: float = 0) -> str:
    """
    Speak text out loud using local TTS.

    Two modes:
    - Preset voices (Kokoro, ~1s): use voice="am_onyx" etc.
    - Voice cloning (~7s): use clone="pedro_pascal" or ref_audio="/path/to/ref.wav"

    Args:
        text: The text to speak out loud
        voice: Kokoro preset voice ID (e.g. "am_onyx", "af_bella"). Use muse_list_voices for options.
        clone: Name of a bundled voice clone (e.g. "pedro_pascal", "idris_elba"). Use muse_list_voices for options.
        ref_audio: Path to a custom reference WAV file for voice cloning (10-30s clean speech, 24kHz mono).
        speed: Speed multiplier for Kokoro voices (default 1.0, range 0.5-2.0). Not used for clones.

    Returns:
        Confirmation message
    """
    # Priority: ref_audio > clone > voice (most specific wins)
    if ref_audio:
        error, engine_name = generate_clone_and_play(text, ref_audio)
        if not error:
            return f"[MUSE clone · custom ref · {engine_name}]\n\n{text}"
        return f"Failed to speak: {error}"

    if clone:
        clone_key = clone.lower().replace(" ", "_")
        if clone_key not in CLONE_VOICES:
            available = ", ".join(sorted(CLONE_VOICES.keys()))
            return f"Unknown clone '{clone}'. Available: {available}"
        error, engine_name = generate_clone_and_play(text, CLONE_VOICES[clone_key])
        if not error:
            display = CLONE_DISPLAY_NAMES.get(clone_key, clone_key)
            return f"[MUSE clone · {display} · {engine_name}]\n\n{text}"
        return f"Failed to speak: {error}"

    # Default: Kokoro preset voice
    voice = voice or KOKORO_VOICE
    speed = speed or KOKORO_SPEED

    if voice not in ALL_VOICE_IDS:
        return f"Unknown voice '{voice}'. Use muse_list_voices to see available voices."

    speed = max(0.5, min(2.0, speed))

    error = generate_and_play(text, voice, speed)
    if not error:
        return f"[MUSE voice · {voice} · {speed}x]\n\n{text}"
    return f"Failed to speak: {error}"


@mcp.tool()
def muse_list_voices(language: str = "") -> str:
    """
    List all available voices — presets and clones.

    Returns Kokoro preset voices grouped by language, plus available voice clones.

    Args:
        language: Optional filter — e.g. "american", "british", "japanese", "clone"

    Returns:
        Formatted list of available voices
    """
    lines = []

    # Voice clones section
    clone_eng = detect_clone_engine()
    clone_engine_label = "IndexTTS-1.5" if clone_eng == "indextts" else "Chatterbox OG"
    show_clones = not language or "clone" in language.lower()
    if show_clones and CLONE_VOICES:
        lines.append(f"Voice Clones ({clone_engine_label} — ~7s generation):\n")
        for clone_id in sorted(CLONE_VOICES.keys()):
            display = CLONE_DISPLAY_NAMES.get(clone_id, clone_id)
            lines.append(f"    {clone_id:20s} {display}")
        lines.append(f"\n  Use: muse_speak(text, clone=\"pedro_pascal\")")
        lines.append(f"  Custom: muse_speak(text, ref_audio=\"/path/to/voice.wav\")")
        lines.append("")

    # Kokoro presets section
    show_presets = not language or "clone" not in language.lower()
    if show_presets:
        lines.append(f"Kokoro Preset Voices (~1s generation, default: {KOKORO_VOICE}):\n")

        for group_name, voices in VOICES.items():
            if language and language.lower() not in group_name.lower() and "clone" not in language.lower():
                continue

            lines.append(f"  {group_name}:")
            for voice_id, display_name in voices:
                marker = " <-- default" if voice_id == KOKORO_VOICE else ""
                lines.append(f"    {voice_id:20s} {display_name}{marker}")
            lines.append("")

    if not lines:
        return f"No voices found matching '{language}'. Try: american, british, spanish, japanese, french, clone"

    clone_count = len(CLONE_VOICES)
    preset_count = len(ALL_VOICE_IDS)
    lines.append(f"Total: {preset_count} presets + {clone_count} clones")
    lines.append("\nSet default: KOKORO_VOICE=am_onyx  KOKORO_SPEED=1.1")

    return "\n".join(lines)


@mcp.tool()
def muse_check() -> dict:
    """
    Check if MUSE TTS is ready to speak.

    Returns status of all TTS engines and platform info.
    """
    engine = detect_engine()
    clone_eng = detect_clone_engine()

    status = {
        "kokoro_engine": engine,
        "clone_engine": clone_eng,
        "platform": f"{platform.system()} {platform.machine()}",
        "default_voice": KOKORO_VOICE,
        "default_speed": KOKORO_SPEED,
        "preset_voices": len(ALL_VOICE_IDS),
        "voice_clones": len(CLONE_VOICES),
    }

    if engine == "mlx":
        status["kokoro_status"] = "ready (mlx_audio — Apple Silicon)"
    elif engine == "kokoro":
        status["kokoro_status"] = "ready (kokoro PyTorch)"
    else:
        status["kokoro_status"] = "not available"

    if clone_eng == "indextts":
        status["clone_status"] = "ready (IndexTTS-1.5 — Apple Silicon)"
    elif clone_eng == "chatterbox":
        status["clone_status"] = "ready (Chatterbox OG — PyTorch)"
    else:
        status["clone_status"] = "not available — install mlx_audio or chatterbox-tts"

    if engine == "none" and clone_eng == "none":
        status["help"] = "Install: pip install mlx_audio (Mac) or pip install kokoro chatterbox-tts (any platform)"

    return status


# ============================================
# MAIN
# ============================================

if __name__ == "__main__":
    engine = detect_engine()
    clone_eng = detect_clone_engine()
    engine_label = {
        "mlx": "mlx_audio (Apple Silicon)",
        "kokoro": "kokoro PyTorch",
        "none": "NOT FOUND",
    }.get(engine, "unknown")
    clone_label = {
        "indextts": "IndexTTS-1.5 (Apple Silicon)",
        "chatterbox": "Chatterbox OG (PyTorch)",
        "none": "NOT FOUND",
    }.get(clone_eng, "unknown")

    log("\n" + "=" * 50)
    log("  MUSE TTS Live v2.0 — Voice Synthesis + Cloning")
    log("  By The Funkatorium")
    log("=" * 50)
    log(f"\n  Kokoro:  {engine_label}")
    log(f"  Cloning: {clone_label}")
    log(f"  Platform:   {platform.system()} {platform.machine()}")
    log(f"  Voice:      {KOKORO_VOICE}")
    log(f"  Speed:      {KOKORO_SPEED}x")
    log(f"  Presets:    {len(ALL_VOICE_IDS)} voices")
    log(f"  Clones:     {len(CLONE_VOICES)} voices")
    log("\n  Tools:")
    log("    muse_speak       — Speak text (preset or clone)")
    log("    muse_list_voices — Browse voices + clones")
    log("    muse_check       — System status")
    log("\n" + "=" * 50 + "\n")

    mcp.run()
