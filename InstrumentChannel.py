import logging

class InstrumentChannel:
    """Abstract base class for all instrument channels."""

    def __init__(self, parent, instrument_name, volume=80):
        self._parent = parent
        self._volume = volume
        self._instrument_registry = parent.get_instrument_registry()
        self.set_instrument(instrument_name)
        self._is_playing = False

    def set_instrument(self, instrument_name):
        """Sets the channel's instrument based on the instrument name."""
        self._instrument_name = instrument_name
        self._synth, self._channel = self._instrument_registry.get_instrument(instrument_name)

    def set_volume(self, volume):
        """Sets the channel's volume."""
        self._volume = volume

    def get_volume(self):
        """Returns the channel's volume."""
        return self._volume

    def get_parent(self):
        """Returns parent"""
        return self._parent

    def play(self):
        """Starts the channel."""
        if not self._is_playing:
            logging.debug(f"Starting channel '{self}'...")
            self._is_playing = True

    def stop(self):
        """Stops the channel."""
        if self._is_playing:
            logging.debug(f"Pausing channel '{self}'...")
            self._is_playing = False

    def tick(self):
        """Reaction on tick step"""
        pass