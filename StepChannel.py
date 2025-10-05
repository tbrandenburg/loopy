import logging

class StepChannel:
    """Abstract base class for all step channels."""

    def __init__(self, instrument_name, volume=80):
        self._instrument_name = instrument_name
        self._volume = volume
        self._is_playing = False
        self._steps = []

    def set_step(self, step, note, velocity):
        # If the step index is greater than the current list, extend the list with None
        if step >= len(self._steps):
            # Add the required number of None values to reach the index
            self._steps.extend([None] * (step + 1 - len(self._steps)))

        # Set the step with the note and velocity
        self._steps[step] = [note, velocity]

    def reset_step(self, step):
        # If the step index is greater than the current list, extend the list with None
        if step >= len(self._steps):
            # Add the required number of None values to reach the index
            self._steps.extend([None] * (step + 1 - len(self._steps)))

        # Reset the step by setting it to None
        self._steps[step] = None

    def set_instrument(self, instrument_name):
        """Sets the channel's instrument based on the instrument name."""
        self._instrument_name = instrument_name

    def get_instrument_name(self):
        """Returns the channel's instrument name."""
        return self._instrument_name

    def set_volume(self, volume):
        """Sets the channel's volume."""
        self._volume = volume

    def get_volume(self):
        """Returns the channel's volume."""
        return self._volume

    def play(self):
        """Starts the channel."""
        if not self._is_playing:
            logging.debug(f"Starting Step Channel {self._instrument_name}...")
            self._is_playing = True

    def stop(self):
        """Stops the channel."""
        if self._is_playing:
            logging.debug(f"Pausing Step Channel {self._instrument_name}...")
            self._is_playing = False

    def get_steps(self):
        return self._steps