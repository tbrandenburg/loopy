#!/usr/bin/env python3
"""Cross-platform installer for FluidSynth and default soundfont bootstrap."""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

DEFAULT_SOUNDFONT_URL = (
    "https://schristiancollins.com/generaluser/GeneralUser_GS_1.471.zip"
)
DEFAULT_SOUNDFONT_NAME = "GeneralUser_GS.sf2"


class InstallationError(RuntimeError):
    """Raised when an installation step fails."""


def run_command(command: Sequence[str]) -> None:
    """Run a command, raising InstallationError on failure."""
    print(f"Running: {' '.join(command)}")
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - direct exit path
        raise InstallationError(
            f"Command {' '.join(command)} failed with exit code {exc.returncode}."
        ) from exc


def detect_package_manager(candidates: Iterable[str]) -> str | None:
    """Return the first available command in *candidates* or ``None``."""
    for candidate in candidates:
        if shutil.which(candidate):
            return candidate
    return None


def install_linux() -> None:
    manager = detect_package_manager(["apt-get", "dnf", "pacman", "zypper"])
    if manager is None:
        raise InstallationError(
            "Unsupported Linux distribution: no known package manager found."
        )

    if manager == "apt-get":
        run_command(["sudo", "apt-get", "update"])
        run_command(["sudo", "apt-get", "install", "-y", "fluidsynth"])
    elif manager == "dnf":
        run_command(["sudo", "dnf", "install", "-y", "fluidsynth"])
    elif manager == "pacman":
        run_command(["sudo", "pacman", "-Sy", "--noconfirm", "fluidsynth"])
    elif manager == "zypper":
        run_command(["sudo", "zypper", "install", "-y", "fluidsynth"])


def install_macos() -> None:
    if not shutil.which("brew"):
        raise InstallationError(
            "Homebrew is required to install FluidSynth automatically on macOS. "
            "Install Homebrew from https://brew.sh/ and re-run this script."
        )
    run_command(["brew", "update"])
    run_command(["brew", "install", "fluid-synth"])


def install_windows() -> None:
    if shutil.which("winget"):
        run_command(["winget", "install", "-e", "--id", "FluidSynth.FluidSynth"])
        return
    if shutil.which("choco"):
        run_command(["choco", "install", "-y", "fluidsynth"])
        return
    raise InstallationError(
        "Neither winget nor Chocolatey are available. Install FluidSynth manually "
        "from https://github.com/FluidSynth/fluidsynth/releases and re-run this script."
    )


def _extract_soundfont(archive_path: Path, soundfont_path: Path) -> None:
    try:
        with ZipFile(archive_path) as archive:
            candidates = [
                name
                for name in archive.namelist()
                if name.lower().endswith(".sf2") and not name.endswith("/")
            ]
            if not candidates:
                raise InstallationError(
                    "Downloaded GeneralUser archive does not contain an .sf2 file."
                )

            # Prefer the shallowest path in the archive to avoid bundled extras.
            candidates.sort(key=lambda name: (name.count("/"), len(name)))
            chosen = candidates[0]
            with archive.open(chosen) as src, open(soundfont_path, "wb") as dest:
                shutil.copyfileobj(src, dest)
    except BadZipFile as exc:  # pragma: no cover - depends on remote file integrity
        raise InstallationError(
            "Downloaded GeneralUser archive is not a valid ZIP file."
        ) from exc


def _copy_soundfont_file(
    source: Path, destination: Path, require_sf2_suffix: bool = True
) -> None:
    if not source.exists():
        raise InstallationError(f"Soundfont source file {source} does not exist.")
    if require_sf2_suffix and source.suffix.lower() != ".sf2":
        raise InstallationError(
            f"Unsupported soundfont file type: {source.suffix or 'no extension'}."
        )
    shutil.copyfile(source, destination)


def _download_to_temp(url: str) -> Path:
    request_headers = {"User-Agent": "loopy-installer/1.0"}
    parsed = urlparse(url)
    if parsed.netloc.endswith("schristiancollins.com"):
        request_headers.setdefault(
            "Referer", "https://schristiancollins.com/generaluser.php"
        )
    request = Request(url, headers=request_headers)

    try:
        with urlopen(request) as response, NamedTemporaryFile(delete=False) as tmp:
            shutil.copyfileobj(response, tmp)
    except HTTPError as exc:  # pragma: no cover - network dependent
        raise InstallationError(
            "Failed to download GeneralUser soundfont archive. "
            f"HTTP status: {exc.code}."
        ) from exc
    except URLError as exc:  # pragma: no cover - network dependent
        raise InstallationError(
            "Failed to download GeneralUser soundfont archive. "
            "Please download it manually from https://schristiancollins.com/generaluser.php "
            "and place the .sf2 file in the target directory."
        ) from exc

    return Path(tmp.name)


def download_soundfont(
    target_dir: Path,
    overwrite: bool = False,
    source: str = DEFAULT_SOUNDFONT_URL,
) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    soundfont_path = target_dir / DEFAULT_SOUNDFONT_NAME

    if soundfont_path.exists() and not overwrite:
        print(f"Soundfont already present at {soundfont_path}, skipping download.")
        return soundfont_path

    parsed = urlparse(source)
    suffix = Path(unquote(parsed.path or "")).suffix.lower()

    if parsed.scheme in ("", "file"):
        if parsed.scheme == "":
            local_path = Path(source)
        else:
            if parsed.netloc not in ("", "localhost"):
                raise InstallationError(
                    f"Unsupported file URL host: {parsed.netloc}."
                )
            path_part = unquote(parsed.path)
            if sys.platform.startswith("win") and path_part.startswith("/") and len(path_part) > 2 and path_part[2] == ":":
                path_part = path_part.lstrip("/")
            local_path = Path(path_part)
        local_path = local_path.expanduser()
        if suffix == ".zip":
            _extract_soundfont(local_path, soundfont_path)
        else:
            _copy_soundfont_file(local_path, soundfont_path, require_sf2_suffix=True)
        print(f"Soundfont saved to {soundfont_path}")
        return soundfont_path

    print(f"Downloading default soundfont archive from {source}")
    tmp_path = _download_to_temp(source)

    try:
        if suffix == ".sf2":
            _copy_soundfont_file(tmp_path, soundfont_path, require_sf2_suffix=False)
        else:
            _extract_soundfont(tmp_path, soundfont_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    print(f"Soundfont saved to {soundfont_path}")
    return soundfont_path


def install_fluidsynth(skip_install: bool) -> None:
    system = platform.system()
    print(f"Detected operating system: {system}")
    if skip_install:
        print("Skipping FluidSynth package installation as requested.")
        return

    if system == "Linux":
        install_linux()
    elif system == "Darwin":
        install_macos()
    elif system == "Windows":
        install_windows()
    else:
        raise InstallationError(
            f"Unsupported operating system: {system}. Please install FluidSynth manually."
        )


def parse_args(args: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip installing FluidSynth (only download the default soundfont).",
    )
    parser.add_argument(
        "--overwrite-soundfont",
        action="store_true",
        help="Re-download the default soundfont even if it already exists.",
    )
    parser.add_argument(
        "--soundfont-dir",
        default=str(Path(__file__).resolve().parent / "sf2"),
        help="Directory where the default soundfont will be stored.",
    )
    parser.add_argument(
        "--soundfont-url",
        default=DEFAULT_SOUNDFONT_URL,
        help="URL or local path to the soundfont archive or .sf2 file.",
    )
    return parser.parse_args(args)


def main(argv: Sequence[str] | None = None) -> int:
    options = parse_args(argv or sys.argv[1:])

    try:
        install_fluidsynth(options.skip_install)
        download_soundfont(
            Path(options.soundfont_dir),
            options.overwrite_soundfont,
            options.soundfont_url,
        )
    except InstallationError as exc:  # pragma: no cover - CLI entry point
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
