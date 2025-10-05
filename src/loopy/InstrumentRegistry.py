import logging
import sys
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .SoundEngine import SoundEngine

# Select the appropriate FluidSynth driver based on the operating system
if sys.platform == "linux" or sys.platform == "linux2":
    DRIVER = "alsa"  # Linux: ALSA or PulseAudio
elif sys.platform == "darwin":
    DRIVER = "coreaudio"  # macOS: CoreAudio
elif sys.platform == "win32":
    DRIVER = "dsound"  # Windows: DirectSound
else:
    DRIVER = "file"  # Fallback driver


@dataclass(frozen=True)
class PresetMetadata:
    """Static metadata about a preset inside a soundfont."""

    soundfont_path: str
    bank: int
    preset: int
    name: str


@dataclass(frozen=True)
class InstrumentOption:
    """Instrument option exposed to the UI for selection."""

    alias: str
    display_name: str
    soundfont_path: str
    bank: int
    preset: int
    preset_name: str

class InstrumentRegistry:
    """Manages instrument IDs and maps them to the SoundEngine."""

    def __init__(self, sound_engine: SoundEngine, max_channels: int = 16):
        """Initialize the instrument registry with a sound engine.

        Args:
            sound_engine (SoundEngine): The sound engine to use for managing instruments.
        """
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._soundfont_cache: Dict[str, int] = {}
        self._sound_engine = sound_engine
        self._available_channels = deque(range(max_channels))
        self._lock = threading.Lock()

        self._soundfont_presets: Dict[str, List[PresetMetadata]] = {}
        self._preset_aliases: Dict[Tuple[str, int, int], str] = {}
        self._preset_to_primary_name: Dict[Tuple[str, int, int], str] = {}
        self._instrument_display_names: Dict[str, str] = {}

    def register_instrument(self, instrument_name, soundfont_path, bank=0, preset=0):
        """Registers an instrument with a soundfont and assigns it to a channel.

        Args:
            instrument_name (str): The name of the instrument to register.
            soundfont_path (str): The file path to the soundfont.
            bank (int, optional): The bank number in the soundfont. Defaults to 0.
            preset (int, optional): The preset number in the soundfont. Defaults to 0.
        """

        # Check if the soundfont is already loaded
        if soundfont_path in self._soundfont_cache:
            sfid = self._soundfont_cache[soundfont_path]
        else:
            sfid = self._sound_engine.load_soundfont(soundfont_path)
            self._soundfont_cache[soundfont_path] = sfid

        with self._lock:
            self._ensure_soundfont_cached(soundfont_path, sfid)

            if instrument_name in self._registry:
                logging.debug("Instrument '%s' already registered.", instrument_name)
                return self._registry[instrument_name]["channel"]

            metadata = self._find_preset_metadata(soundfont_path, bank, preset)
            preset_key = (soundfont_path, bank, preset)

            primary_name = self._preset_to_primary_name.get(preset_key)
            if primary_name:
                entry = self._registry.get(primary_name)
                if entry is not None:
                    self._registry[instrument_name] = entry
                    display = self._build_display_name(soundfont_path, metadata.name if metadata else instrument_name, bank, preset)
                    self._instrument_display_names[instrument_name] = display
                    self._preset_aliases.setdefault(preset_key, self._build_default_alias(soundfont_path, bank, preset))
                    logging.debug(
                        "Reusing MIDI channel %d for instrument '%s' (alias of '%s').",
                        entry["channel"],
                        instrument_name,
                        primary_name,
                    )
                    return entry["channel"]

            if not self._available_channels:
                raise RuntimeError("No MIDI channels available for new instruments.")

            available_channel = self._available_channels.popleft()

            self._sound_engine.select_instrument(available_channel, sfid, bank, preset)
            self._registry[instrument_name] = {
                "channel": available_channel,
                "sfid": sfid,
                "bank": bank,
                "preset": preset,
                "soundfont_path": soundfont_path,
            }
            self._preset_to_primary_name.setdefault(preset_key, instrument_name)
            self._preset_aliases.setdefault(preset_key, self._build_default_alias(soundfont_path, bank, preset))

            display_name = self._build_display_name(
                soundfont_path,
                metadata.name if metadata else instrument_name,
                bank,
                preset,
            )
            self._instrument_display_names[instrument_name] = display_name

            channel_info = self._sound_engine.channel_info(available_channel)

            logging.debug(
                f"Registered '{channel_info.name}' (bank={bank},preset={preset}) "
                f"for channel {available_channel} and mapped to '{instrument_name}'!"
            )

            return available_channel

    def _ensure_soundfont_cached(self, soundfont_path: str, sfid: int) -> None:
        """Populate preset metadata for a soundfont if necessary."""

        if soundfont_path in self._soundfont_presets:
            return

        presets: List[PresetMetadata] = []
        try:
            raw_presets = self._sound_engine.list_presets(sfid)
        except AttributeError:
            raw_presets = []
        except Exception:  # pragma: no cover - defensive logging for backends without support
            logging.exception("Failed to enumerate presets for soundfont '%s'.", soundfont_path)
            raw_presets = []

        if not raw_presets:
            logging.debug("Soundfont '%s' did not expose preset metadata.", soundfont_path)

        for preset in raw_presets:
            name = preset.get("name")
            bank = preset.get("bank")
            program = preset.get("preset")
            if name is None or bank is None or program is None:
                continue
            metadata = PresetMetadata(soundfont_path, bank, program, name)
            presets.append(metadata)
            key = (soundfont_path, bank, program)
            self._preset_aliases.setdefault(key, self._build_default_alias(soundfont_path, bank, program))

        self._soundfont_presets[soundfont_path] = presets

    def _find_preset_metadata(self, soundfont_path: str, bank: int, preset: int) -> Optional[PresetMetadata]:
        """Find the cached metadata for a preset if available."""

        for metadata in self._soundfont_presets.get(soundfont_path, []):
            if metadata.bank == bank and metadata.preset == preset:
                return metadata
        return None

    def _build_default_alias(self, soundfont_path: str, bank: int, preset: int) -> str:
        """Return a deterministic alias for a preset."""

        stem = Path(soundfont_path).stem or soundfont_path
        return f"{stem}:{bank}:{preset}"

    def _build_display_name(self, soundfont_path: str, preset_name: str, bank: int, preset: int) -> str:
        """Generate a human friendly label for a preset."""

        stem = Path(soundfont_path).stem or soundfont_path
        title = preset_name or f"Program {preset}"
        return f"{title} ({bank}:{preset}) — {stem}"

    def get_instrument(self, instrument_name):
        """Returns the SoundEngine instance and the instrument's channel.

        Args:
            instrument_name (str): The name of the instrument to retrieve.

        Returns:
            list: A list containing the SoundEngine and the instrument channel
        """
        instrument = self._registry.get(instrument_name)
        if instrument:
            return self._sound_engine, instrument["channel"]
        return None, None

    def get_instrument_descriptor(self, instrument_name: str) -> Optional[Dict[str, object]]:
        """Return metadata about a registered instrument."""

        with self._lock:
            entry = self._registry.get(instrument_name)
            if entry is None:
                return None

            metadata = self._find_preset_metadata(
                entry.get("soundfont_path", ""),
                entry.get("bank", 0),
                entry.get("preset", 0),
            )
            alias_key = (
                entry.get("soundfont_path", ""),
                entry.get("bank", 0),
                entry.get("preset", 0),
            )
            return {
                "soundfont_path": entry.get("soundfont_path"),
                "bank": entry.get("bank"),
                "preset": entry.get("preset"),
                "preset_name": metadata.name if metadata else None,
                "display_name": self._instrument_display_names.get(instrument_name, instrument_name),
                "alias": self._preset_aliases.get(alias_key),
            }

    def get_instrument_display_name(self, instrument_name: str) -> str:
        """Return a human friendly name for an instrument, falling back to its key."""

        with self._lock:
            return self._instrument_display_names.get(instrument_name, instrument_name)

    def unregister_instrument(self, instrument_name):
        """Remove an instrument and release its MIDI channel."""
        with self._lock:
            instrument = self._registry.pop(instrument_name, None)
            if instrument is not None:
                self._available_channels.append(instrument["channel"])

    def get_sound_engine(self):
        """Expose the underlying sound engine."""
        return self._sound_engine

    def list_registered_instruments(self):
        """List all registered instruments.

        Returns:
            list: A list of registered instrument names.
        """
        return list(self._registry.keys())

    def list_available_instruments(self) -> List[InstrumentOption]:
        """Return all known presets as instrument options."""

        with self._lock:
            options: List[InstrumentOption] = []
            for soundfont_path, presets in self._soundfont_presets.items():
                for metadata in presets:
                    alias_key = (soundfont_path, metadata.bank, metadata.preset)
                    alias = self._preset_aliases.get(alias_key)
                    if alias is None:
                        alias = self._build_default_alias(soundfont_path, metadata.bank, metadata.preset)
                        self._preset_aliases[alias_key] = alias
                    display = self._build_display_name(soundfont_path, metadata.name, metadata.bank, metadata.preset)
                    options.append(
                        InstrumentOption(
                            alias=alias,
                            display_name=display,
                            soundfont_path=soundfont_path,
                            bank=metadata.bank,
                            preset=metadata.preset,
                            preset_name=metadata.name,
                        )
                    )

        options.sort(key=lambda option: (Path(option.soundfont_path).name.lower(), option.bank, option.preset))
        return options
