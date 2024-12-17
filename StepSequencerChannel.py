from InstrumentChannel import InstrumentChannel

class StepSequencerChannel(InstrumentChannel):
    """A channel for a step sequencer."""

    def __init__(self, project, sequencer, name, volume=80):
        super().__init__(project, name, volume)
        self._sequencer = sequencer

    def get_sequencer(self):
        """Returns sequencer"""
        return self._sequencer

    def play(self):
        """Starts the channel"""
        super().play()  # Set the channel to "play"
        if self._is_playing:
            self._sequencer.play()

    def stop(self):
        """Stops the channel"""
        super().stop()  # Set the channel to "stop"
        if not self._is_playing:
            self._sequencer.stop()