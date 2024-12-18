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