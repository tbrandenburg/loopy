import logging

from InstrumentChannel import InstrumentChannel


class StepSequencerChannel(InstrumentChannel):
    """A channel for a step sequencer."""

    def __init__(self, project, name, volume=80):
        try:
            super().__init__(project, name, volume)
        except KeyError:
            logging.debug(
                "Instrument '%s' is not registered — continuing without a synth binding.",
                name,
            )
            self._parent = project
            self._instrument_registry = project.get_instrument_registry()
            self._instrument_name = name
            self._volume = volume
            self._is_playing = False
            self._synth = None
            self._channel = None

    def get_sequencer(self):
        """Returns sequencer"""
        return self._parent.get_sequencer()

    def play(self):
        """Starts the channel"""
        super().play()  # Set the channel to "play"

    def stop(self):
        """Stops the channel"""
        super().stop()  # Set the channel to "stop"