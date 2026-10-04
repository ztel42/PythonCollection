"""Burn altitude/speed (and optional lat/lon) HUD via ASS + ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Union

from .models import TelemetryFrame

PathLike = Union[str, Path]


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def ensure_ffmpeg() -> str:
    """Return path to ffmpeg, attempting a package install if missing."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    # Best-effort install on this Linux box (Debian/Ubuntu style).
    for cmd in (
        ["apt-get", "update"],
        ["apt-get", "install", "-y", "ffmpeg"],
    ):
        try:
            subprocess.run(cmd, check=False, capture_output=True, timeout=180)
        except (OSError, subprocess.TimeoutExpired):
            break
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError(
            "ffmpeg is required for HUD burn but could not be found or installed"
        )
    return path


def _fmt_speed(frame: TelemetryFrame) -> str:
    if frame.speed_mps is None:
        return "spd: --"
    src = "rec" if frame.speed_source == "recorded" else "est"
    return f"spd: {frame.speed_mps:.1f} m/s ({src})"


def _fmt_alt(frame: TelemetryFrame) -> str:
    tag = "abs" if frame.altitude_source == "absolute" else "rel"
    return f"alt: {frame.altitude_m:.1f} m ({tag})"


def frames_to_ass(
    frames: List[TelemetryFrame],
    *,
    include_latlon: bool = True,
    play_res_x: int = 1280,
    play_res_y: int = 720,
) -> str:
    """Build a minimal ASS/SSA script with one dialogue event per frame cue."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HUD,DejaVu Sans,28,&H00FFFFFF,&H000000FF,&H80000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,0,7,20,20,20,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for fr in frames:
        parts = [_fmt_alt(fr), _fmt_speed(fr)]
        if include_latlon:
            parts.append(f"lat: {fr.latitude:.6f}  lon: {fr.longitude:.6f}")
        text = r"\N".join(parts)
        # Escape ASS specials lightly
        text = text.replace("{", r"\{").replace("}", r"\}")
        lines.append(
            f"Dialogue: 0,{fr.cue_start_ass},{fr.cue_end_ass},HUD,,0,0,0,,{text}\n"
        )
    return "".join(lines)


def burn_hud(
    video: PathLike,
    frames: List[TelemetryFrame],
    out: PathLike,
    *,
    include_latlon: bool = False,
) -> Path:
    """Generate ASS from frames and burn into video with ffmpeg -vf ass=...

    Source video and SRT-derived data are read-only; only ``out`` is written.
    """
    video_path = Path(video)
    out_path = Path(out)
    if not video_path.is_file():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not frames:
        raise ValueError("No telemetry frames to burn into HUD")

    ffmpeg = ensure_ffmpeg()
    ass_text = frames_to_ass(frames, include_latlon=include_latlon)

    with tempfile.TemporaryDirectory(prefix="flight_hud_") as tmp:
        ass_path = Path(tmp) / "hud.ass"
        ass_path.write_text(ass_text, encoding="utf-8")
        # Escape path for ffmpeg filter (colons / backslashes)
        ass_filter = str(ass_path).replace("\\", "/").replace(":", r"\:")
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"ass={ass_filter}",
            "-c:a",
            "copy",
            str(out_path),
        ]
        # Silent lavfi test videos have no audio — allow failure on -c:a copy
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            # Retry without audio copy (generated silent clips)
            cmd_no_a = [
                ffmpeg,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"ass={ass_filter}",
                "-an",
                str(out_path),
            ]
            proc2 = subprocess.run(cmd_no_a, capture_output=True, text=True)
            if proc2.returncode != 0:
                raise RuntimeError(
                    "ffmpeg HUD burn failed:\n"
                    + (proc2.stderr or proc.stderr or "unknown error")
                )

    if not out_path.is_file() or out_path.stat().st_size == 0:
        raise RuntimeError(f"HUD output was not created: {out_path}")
    return out_path


def make_silent_test_video(
    path: PathLike, *, duration_s: float = 3.0, size: str = "640x360"
) -> Path:
    """Generate a short silent test MP4 with lavfi (no drone footage required)."""
    ffmpeg = ensure_ffmpeg()
    out = Path(path)
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=blue:s={size}:d={duration_s}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-t",
        str(duration_s),
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.is_file():
        raise RuntimeError(
            "Failed to generate test video:\n" + (proc.stderr or "unknown")
        )
    return out


def probe_is_video(path: PathLike) -> bool:
    """Return True if ffprobe sees a video stream."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return False
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "csv=p=0",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0 and "video" in (proc.stdout or "")
