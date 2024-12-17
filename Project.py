from InstrumentRegistry import InstrumentRegistry


import logging
import threading
import time


class Project:
    """The project that manages the beat logic and controls channels."""

    def __init__(self, bpm=120, beats_per_measure=4):
        self._instrument_registry = InstrumentRegistry(self)  # Reference to the InstrumentRegistry
        self._bpm = bpm
        self._beats_per_measure = beats_per_measure
        self._seconds_per_beat = 60 / bpm  # Calculate seconds per beat (for the metronome)
        self._channels = []
        self._is_playing = False
        self._lock = threading.Lock()  # For synchronizing the tick steps

    def get_instrument_registry(self):
        """Returns the Instrument Registry."""
        return self._instrument_registry

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
        self._channels.append(channel)

    def remove_channel(self, channel):
        """Removes a channel from the project."""
        self._channels.remove(channel)

    def get_channels(self):
        """Returns all channels"""
        return self._channels

    def start_ticking(self):
        """Starts the beat management and notifies all channels."""
        self._is_playing = True
        while self._is_playing:
            with self._lock:
                for tick in range(self._beats_per_measure):
                    # Notify all channels that a tick has occurred
                    for channel in self._channels:
                        channel.tick()
                    time.sleep(self.get_seconds_per_beat())  # Wait until the next beat

    def play(self):
        """Starts the project and all channels."""
        logging.debug("Starting the project.")
        threading.Thread(target=self.start_ticking).start()
        for channel in self._channels:
            logging.debug("Starting channel: %s", channel)
            channel.play()

    def stop(self):
        """Stops the project and all channels."""
        logging.debug("Stopping the project.")
        self._is_playing = False
        for channel in self._channels:
            logging.debug("Stopping channel: %s", channel)
            channel.stop()