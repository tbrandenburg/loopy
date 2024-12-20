from InstrumentChannel import InstrumentChannel

class StepSequencerChannel(InstrumentChannel):
    """A channel for a step sequencer."""

    def __init__(self, project, name, volume=80):
        super().__init__(project, name, volume)
        
    def get_sequencer(self):
        """Returns sequencer"""
        return self._parent.get_soundengine()

    def play(self):
        """Starts the channel"""
        super().play()  # Set the channel to "play"

    def stop(self):
        """Stops the channel"""
        super().stop()  # Set the channel to "stop"