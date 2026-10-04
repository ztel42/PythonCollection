"""CLI entry for Flight Telemetry Tools."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .export_gpx import write_gpx
from .export_kml import write_kml
from .hud import burn_hud, ffmpeg_available
from .parser import parse_srt_file


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="flight-telemetry",
        description=(
            "Parse DJI .SRT flight telemetry into GPX/KML tracks, "
            "or burn an altitude/speed HUD into video with ffmpeg."
        ),
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = p.add_subparsers(dest="command", required=True)

    parse_p = sub.add_parser(
        "parse",
        help="Parse a DJI .SRT file and export GPX and/or KML",
    )
    parse_p.add_argument(
        "srt",
        metavar="SRT",
        help="Path to DJI .SRT sidecar (read-only)",
    )
    parse_p.add_argument(
        "--gpx",
        metavar="PATH",
        help="Write GPX 1.1 track to PATH",
    )
    parse_p.add_argument(
        "--kml",
        metavar="PATH",
        help="Write KML 2.2 (LineString + gx:Track) to PATH",
    )
    parse_p.add_argument(
        "--name",
        default="DJI flight track",
        help="Track name in GPX/KML (default: DJI flight track)",
    )

    burn_p = sub.add_parser(
        "burn",
        help="Burn altitude/speed HUD into a video using ffmpeg + ASS",
    )
    burn_p.add_argument(
        "video",
        metavar="VIDEO",
        help="Path to video file (read-only)",
    )
    burn_p.add_argument(
        "--srt",
        metavar="PATH",
        help="Path to sibling .SRT (default: same stem as VIDEO with .SRT/.srt)",
    )
    burn_p.add_argument(
        "--out",
        metavar="PATH",
        required=True,
        help="Output video path",
    )
    burn_p.add_argument(
        "--no-latlon",
        action="store_true",
        help="Omit lat/lon from the HUD overlay",
    )
    return p


def _resolve_sibling_srt(video: Path, explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit)
    for ext in (".SRT", ".srt"):
        cand = video.with_suffix(ext)
        if cand.is_file():
            return cand
    raise FileNotFoundError(
        f"No sibling .SRT found for {video}; pass --srt PATH"
    )


def cmd_parse(args: argparse.Namespace) -> int:
    srt_path = Path(args.srt)
    if not args.gpx and not args.kml:
        print(
            "error: specify at least one of --gpx or --kml",
            file=sys.stderr,
        )
        return 2
    try:
        frames = parse_srt_file(srt_path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: cannot read SRT: {exc}", file=sys.stderr)
        return 1

    if not frames:
        print(
            f"error: no GPS frames found in {srt_path}",
            file=sys.stderr,
        )
        return 1

    rec = sum(1 for f in frames if f.speed_source == "recorded")
    est = sum(1 for f in frames if f.speed_source == "estimated")
    print(
        f"Parsed {len(frames)} GPS frames from {srt_path.name} "
        f"(speed: {rec} recorded, {est} estimated)"
    )
    if args.gpx:
        write_gpx(frames, args.gpx, name=args.name)
        print(f"Wrote GPX: {args.gpx}")
    if args.kml:
        write_kml(frames, args.kml, name=args.name)
        print(f"Wrote KML: {args.kml}")
    return 0


def cmd_burn(args: argparse.Namespace) -> int:
    video = Path(args.video)
    if not video.is_file():
        print(f"error: video not found: {video}", file=sys.stderr)
        return 1
    try:
        srt_path = _resolve_sibling_srt(video, args.srt)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not ffmpeg_available():
        try:
            from .hud import ensure_ffmpeg

            ensure_ffmpeg()
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    try:
        frames = parse_srt_file(srt_path)
    except (FileNotFoundError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not frames:
        print(
            f"error: no GPS frames found in {srt_path}",
            file=sys.stderr,
        )
        return 1

    try:
        out = burn_hud(
            video,
            frames,
            args.out,
            include_latlon=not args.no_latlon,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote HUD video: {out}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "parse":
        return cmd_parse(args)
    if args.command == "burn":
        return cmd_burn(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
