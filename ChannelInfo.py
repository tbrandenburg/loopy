class ChannelInfo:
    """A data structure to hold channel information."""

    def __init__(self, channel, soundfont_id, bank, preset, name):
        """Initialize ChannelInfo.

        Args:
            channel (int): The channel number.
            soundfont_id (int): The ID of the soundfont used.
            bank (int): The bank number.
            preset (int): The preset number.
            name (str): The name of the instrument assigned to the channel.
        """
        self.channel = channel
        self.soundfont_id = soundfont_id
        self.bank = bank
        self.preset = preset
        self.name = name

    def __repr__(self):
        return (f"ChannelInfo(channel={self.channel}, soundfont_id={self.soundfont_id}, "
                f"bank={self.bank}, preset={self.preset}, name='{self.name}')")