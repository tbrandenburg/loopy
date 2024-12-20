from abc import ABC, abstractmethod


class SoundEngine(ABC):
    """Abstract base class for a Sound Engine."""

    @abstractmethod
    def start(self):
        """Start the sound engine with the appropriate driver."""
        pass

    @abstractmethod
    def load_soundfont(self, soundfont_path):
        """Load a soundfont file into the sound engine.

        Args:
            soundfont_path (str): The file path to the soundfont.

        Returns:
            int: The ID of the loaded soundfont.
        """
        pass

    @abstractmethod
    def select_instrument(self, channel, sfid, bank, preset):
        """Select a instrument (program) on a specific channel.

        Args:
            channel (int): The channel number to assign the instrument.
            sfid (int): The soundfont ID.
            bank (int): The bank number in the soundfont.
            preset (int): The preset number in the soundfont.
        """
        pass

    @abstractmethod
    def channel_info(self, channel):
        """Retrieve information about a specific channel.

        Args:
            channel (int): The channel number to query.

        Returns:
            ChannelInfo: Information about the channel, abstracted into a ChannelInfo structure.
        """
        pass

    @abstractmethod
    def get_steps(self):
        """Returns the number of steps of underlying step sequencer."""
        pass

    @abstractmethod
    def add_channel(self, channel):
        """Adds a channel to the step sequencer."""
        pass

    @abstractmethod
    def remove_channel(self, channel):
        """Removes a channel from the step sequencer."""
        pass

    @abstractmethod
    def get_channels(self):
        """Returns all step sequencer channels."""
        pass

    @abstractmethod
    def update(self):
        """Loads the notes of the step channels into the sequence."""
        pass

    @abstractmethod
    def synch_noteon(self, channel, note, velocity=80):
        """Synchronously plays a note on the specified channel."""
        pass

    @abstractmethod
    def synch_noteoff(self, channel, note, velocity=80):
        """Synchronously stops a note on the specified channel."""
        pass