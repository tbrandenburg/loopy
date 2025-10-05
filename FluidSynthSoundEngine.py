from ChannelInfo import ChannelInfo
from InstrumentRegistry import DRIVER
from SoundEngine import SoundEngine


import fluidsynth

import logging


class FluidSynthSoundEngine(SoundEngine):
    """Concrete implementation of SoundEngine using FluidSynth."""

    def __init__(self):
        """Initialize the FluidSynth sound engine instance."""
        self._synth = fluidsynth.Synth()
        self._is_playing = False

    def start(self):
        """Start the FluidSynth engine with the configured driver."""
        if self._is_playing:
            logging.debug("FluidSynthSoundEngine is already running.")
            return

        self._synth.start(driver=DRIVER)
        self._is_playing = True
        logging.debug("FluidSynthSoundEngine started.")

    def stop(self):
        """Stop the FluidSynth engine."""
        if not self._is_playing:
            return

        # Fluidsynth's Python bindings do not expose a dedicated stop call,
        # therefore we simply mark the engine as stopped. Projects should
        # dispose the engine instance if they need a fresh start.
        self._is_playing = False
        logging.debug("FluidSynthSoundEngine stopped.")

    def get_synth(self):
        return self._synth

    def load_soundfont(self, soundfont_path):
        """Load a soundfont into FluidSynth.

        Args:
            soundfont_path (str): The file path to the soundfont.

        Returns:
            int: The ID of the loaded soundfont.
        """
        return self._synth.sfload(soundfont_path)

    def select_instrument(self, channel, sfid, bank, preset):
        """Select an instrument on the specified channel in FluidSynth.

        Args:
            channel (int): The channel number to assign the instrument.
            sfid (int): The soundfont ID.
            bank (int): The bank number in the soundfont.
            preset (int): The preset number in the soundfont.
        """
        self._synth.program_select(channel, sfid, bank, preset)

    def channel_info(self, channel):
        """Retrieve information about a specific channel in FluidSynth.

        Args:
            channel (int): The channel number to query.

        Returns:
            ChannelInfo: Information about the channel, encapsulated in a ChannelInfo structure.
        """
        info = self._synth.channel_info(channel)
        return ChannelInfo(channel=channel,
                           soundfont_id=info[0],
                           bank=info[1],
                           preset=info[2],
                           name=info[3])

    def synch_noteon(self, channel, note, velocity=80):
        self._synth.noteon(channel, note, velocity)

    def synch_noteoff(self, channel, note, velocity=80):
        self._synth.noteoff(channel, note)