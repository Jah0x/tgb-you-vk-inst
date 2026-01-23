from __future__ import annotations

import subprocess
from pathlib import Path


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _get_duration_seconds(path: Path) -> int | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.SubprocessError:
        return None
    try:
        return int(float(result.stdout.strip()))
    except ValueError:
        return None


def download_video(
    url: str,
    tmp_dir: Path,
    formats: list[str],
    max_duration_sec: int,
    max_filesize_mb: int,
    cookies_path: Path | None = None,
) -> Path:
    if cookies_path and not cookies_path.exists():
        raise RuntimeError(f"Cookies file not found: {cookies_path}")
    for format_selector in formats:
        base = tmp_dir / "video"
        output_template = f"{base}.%(ext)s"
        for item in tmp_dir.glob("video.*"):
            item.unlink(missing_ok=True)
        command = [
            "yt-dlp",
            "--no-playlist",
            "--merge-output-format",
            "mp4",
            "-f",
            format_selector,
            "-o",
            output_template,
        ]
        if cookies_path:
            command.extend(["--cookies", str(cookies_path)])
        command.append(url)
        try:
            _run(command)
        except subprocess.CalledProcessError:
            continue
        candidates = list(tmp_dir.glob("video.*"))
        if not candidates:
            continue
        candidate = candidates[0]
        duration = _get_duration_seconds(candidate)
        if duration and duration > max_duration_sec:
            continue
        size_mb = candidate.stat().st_size / (1024 * 1024)
        if size_mb > max_filesize_mb:
            continue
        return candidate
    raise RuntimeError("Failed to download video within limits")


def faststart(input_path: Path, output_path: Path) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
