import logging
import threading
import time
from typing import List

from .StepChannel import StepChannel


class StepSequencer:
    """Backend-agnostic step sequencer that drives StepChannel patterns."""

    def __init__(self, instrument_registry, steps: int = 32, bpm: int = 120):
        self._instrument_registry = instrument_registry
        self._sound_engine = instrument_registry.get_sound_engine()
        self._steps = max(1, steps)
        self._bpm = bpm
        self._step_duration = 60.0 / bpm

        self._channels: List[StepChannel] = []
        self._active_notes = {}
        self._lock = threading.Lock()

        self._current_step = 0
        self._is_running = False
        self._thread = None
        self._stop_event = threading.Event()

    def set_tempo(self, bpm: int):
        """Update the sequencer tempo."""
        with self._lock:
            self._bpm = bpm
            self._step_duration = 60.0 / bpm

    def add_channel(self, channel: StepChannel):
        """Attach a step channel to the sequencer."""
        with self._lock:
            if channel in self._channels:
                return
            self._channels.append(channel)
            self._active_notes[channel] = set()

    def remove_channel(self, channel: StepChannel):
        """Detach a step channel from the sequencer."""
        with self._lock:
            if channel in self._channels:
                self._stop_active_notes(channel)
                self._channels.remove(channel)
                self._active_notes.pop(channel, None)

    def get_channels(self):
        """Return a snapshot of the registered channels."""
        with self._lock:
            return list(self._channels)

    def start(self):
        if self._is_running:
            return

        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._run, name="step-sequencer", daemon=True)
        self._thread.start()

    def stop(self):
        if not self._is_running:
            return

        self._is_running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join()
            self._thread = None

        with self._lock:
            for channel in list(self._channels):
                self._stop_active_notes(channel)
            self._current_step = 0

    def _run(self):
        while not self._stop_event.is_set():
            loop_start = time.perf_counter()
            step_duration = self.advance_one_step()
            elapsed = time.perf_counter() - loop_start
            wait_time = max(0.0, step_duration - elapsed)
            if self._stop_event.wait(wait_time):
                break

    def advance_one_step(self) -> float:
        """Synchronously process a single step iteration.

        Returns the currently configured step duration so callers can
        synchronise their own timing if required.
        """

        with self._lock:
            channels_snapshot = list(self._channels)
            step_index = self._current_step
            self._current_step = (self._current_step + 1) % self._steps
            step_duration = self._step_duration

        for channel in channels_snapshot:
            try:
                self._play_channel_step(channel, step_index)
            except Exception:  # pragma: no cover - defensive logging
                logging.exception("StepSequencer failed to play step for channel %s", channel)

        return step_duration

    def _play_channel_step(self, channel: StepChannel, step_index: int):
        steps = channel.get_steps()
        if not steps:
            self._stop_active_notes(channel)
            return

        step = steps[step_index % len(steps)] if steps else None

        # Release previously held notes
        self._stop_active_notes(channel)

        if not step:
            return

        note, velocity = step
        if note is None:
            return

        _, midi_channel = self._instrument_registry.get_instrument(channel.get_instrument_name())
        if midi_channel is None:
            logging.warning("Instrument '%s' is not registered", channel.get_instrument_name())
            return

        final_velocity = velocity if velocity is not None else channel.get_volume()
        self._sound_engine.synch_noteon(midi_channel, note, final_velocity)
        self._active_notes[channel].add((midi_channel, note))

    def _stop_active_notes(self, channel: StepChannel):
        active = self._active_notes.get(channel)
        if not active:
            return

        for midi_channel, note in list(active):
            self._sound_engine.synch_noteoff(midi_channel, note)
            active.discard((midi_channel, note))
