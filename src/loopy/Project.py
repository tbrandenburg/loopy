from concurrent.futures import ThreadPoolExecutor, wait
import logging
import threading
import time

from .InstrumentRegistry import InstrumentRegistry
from .StepSequencer import StepSequencer


class Project:
    """The project that manages tempo, channels, and sequencing."""

    def __init__(self, soundengine, bpm=120, beats_per_measure=4):
        self._soundengine = soundengine
        self._instrument_registry = InstrumentRegistry(soundengine)
        self._sequencer = StepSequencer(self._instrument_registry, bpm=bpm)

        self._bpm = bpm
        self._beats_per_measure = beats_per_measure
        self._seconds_per_beat = 60 / bpm

        self._channels = []
        self._is_playing = False
        self._lock = threading.Lock()

        self._tick_thread = None
        self._executor = None

    def get_instrument_registry(self):
        """Returns the Instrument Registry."""
        return self._instrument_registry

    def get_sequencer(self):
        """Expose the project's sequencer."""
        return self._sequencer

    def get_soundengine(self):
        """Expose the underlying sound engine."""
        return self._soundengine

    def get_bpm(self):
        """Returns the project's BPM."""
        return self._bpm

    def get_beats_per_measure(self):
        """Returns the project's beats per measure."""
        return self._beats_per_measure

    def get_seconds_per_beat(self):
        """Returns the seconds per beat based on the BPM."""
        return self._seconds_per_beat

    def add_channel(self, channel):
        """Adds a channel to the project."""
        with self._lock:
            self._channels.append(channel)

    def remove_channel(self, channel):
        """Removes a channel from the project."""
        with self._lock:
            if channel in self._channels:
                self._channels.remove(channel)

    def get_channels(self):
        """Returns all channels."""
        with self._lock:
            return list(self._channels)

    def _run_tick_loop(self):
        while self._is_playing:
            tick_start = time.perf_counter()
            with self._lock:
                channels_snapshot = list(self._channels)

            futures = []
            for channel in channels_snapshot:
                futures.append(self._executor.submit(self._safe_tick, channel))

            if futures:
                _, not_done = wait(futures, timeout=self._seconds_per_beat)
                if not_done:
                    logging.warning(
                        "Tick handlers exceeded beat duration on %d channel(s).",
                        len(not_done),
                    )

            elapsed = time.perf_counter() - tick_start
            remaining = max(0.0, self._seconds_per_beat - elapsed)
            time.sleep(remaining)

    def _safe_tick(self, channel):
        try:
            channel.tick()
        except Exception:  # pragma: no cover - defensive logging
            logging.exception("Channel '%s' raised an error during tick.", channel)

    def play(self):
        """Starts the project and all channels."""
        if self._is_playing:
            logging.debug("Project is already playing.")
            return

        logging.debug("Starting the project.")
        self._soundengine.start()
        self._sequencer.set_tempo(self._bpm)
        self._sequencer.start()

        with self._lock:
            channels_snapshot = list(self._channels)

        for channel in channels_snapshot:
            logging.debug("Starting channel: %s", channel)
            channel.play()

        worker_count = max(4, len(channels_snapshot) or 1)
        self._executor = ThreadPoolExecutor(max_workers=worker_count)
        self._is_playing = True

        self._tick_thread = threading.Thread(target=self._run_tick_loop, name="loopy-ticker", daemon=True)
        self._tick_thread.start()

    def stop(self):
        """Stops the project and all channels."""
        if not self._is_playing:
            logging.debug("Project is not playing.")
        else:
            logging.debug("Stopping the project.")
        self._is_playing = False

        if self._tick_thread:
            self._tick_thread.join()
            self._tick_thread = None

        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

        with self._lock:
            channels_snapshot = list(self._channels)

        for channel in channels_snapshot:
            logging.debug("Stopping channel: %s", channel)
            channel.stop()

        self._sequencer.stop()
        self._soundengine.stop()
