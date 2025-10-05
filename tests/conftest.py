from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from loopy.ChannelInfo import ChannelInfo


class FakeSoundEngine:
    """Minimal sound engine stub for isolated tests."""

    def __init__(self):
        self.loaded_soundfonts: dict[str, int] = {}
        self.selected_instruments: dict[int, tuple[int, int, int]] = {}
        self.note_events: list[tuple[str, int, int, int | None]] = []

    def load_soundfont(self, path: str) -> int:
        sfid = self.loaded_soundfonts.setdefault(path, len(self.loaded_soundfonts) + 1)
        return sfid

    def select_instrument(self, channel: int, sfid: int, bank: int, preset: int) -> None:
        self.selected_instruments[channel] = (sfid, bank, preset)

    def channel_info(self, channel: int) -> ChannelInfo:
        return ChannelInfo(channel=channel, soundfont_id=0, bank=0, preset=0, name=f"Channel {channel}")

    def list_presets(self, sfid: int) -> list[dict[str, int | str]]:
        return [{"name": "Concert Grand", "bank": 0, "preset": 0}]

    def synch_noteon(self, midi_channel: int, note: int, velocity: int) -> None:
        self.note_events.append(("on", midi_channel, note, velocity))

    def synch_noteoff(self, midi_channel: int, note: int) -> None:
        self.note_events.append(("off", midi_channel, note, None))


@pytest.fixture
def fake_sound_engine() -> FakeSoundEngine:
    return FakeSoundEngine()


@pytest.fixture
def instrument_registry(fake_sound_engine: FakeSoundEngine):
    from loopy.InstrumentRegistry import InstrumentRegistry

    return InstrumentRegistry(fake_sound_engine)
