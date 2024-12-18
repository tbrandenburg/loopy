import sys
import logging

from SoundEngine import SoundEngine

# Select the appropriate FluidSynth driver based on the operating system
if sys.platform == "linux" or sys.platform == "linux2":
    DRIVER = "alsa"  # Linux: ALSA or PulseAudio
elif sys.platform == "darwin":
    DRIVER = "coreaudio"  # macOS: CoreAudio
elif sys.platform == "win32":
    DRIVER = "dsound"  # Windows: DirectSound
else:
    DRIVER = "file"  # Fallback driver

class InstrumentRegistry:
    """Manages instrument IDs and maps them to the SoundEngine."""

    def __init__(self, sound_engine: SoundEngine):
        """Initialize the instrument registry with a sound engine.

        Args:
            sound_engine (SoundEngine): The sound engine to use for managing instruments.
        """
        self._registry = {}  # Stores information about instruments and their channels
        self._soundfont_cache = {}  # Caches loaded soundfonts (path -> sfid)
        self._sound_engine = sound_engine
        self._sound_engine.start()  # Initialize the sound engine

    def register_instrument(self, instrument_name, soundfont_path, bank=0, preset=0):
        """Registers an instrument with a soundfont and assigns it to a channel.

        Args:
            instrument_name (str): The name of the instrument to register.
            soundfont_path (str): The file path to the soundfont.
            bank (int, optional): The bank number in the soundfont. Defaults to 0.
            preset (int, optional): The preset number in the soundfont. Defaults to 0.
        """

        # Check if the soundfont is already loaded
        if soundfont_path in self._soundfont_cache:
            sfid = self._soundfont_cache[soundfont_path]
        else:
            sfid = self._sound_engine.load_soundfont(soundfont_path)
            self._soundfont_cache[soundfont_path] = sfid

        # Select the program on a new channel
        available_channel = len(self._registry) % 16  # Simple round-robin approach

        self._sound_engine.select_instrument(available_channel, sfid, bank, preset)
        self._registry[instrument_name] = {
            "channel": available_channel,
            "sfid": sfid,
            "bank": bank,
            "preset": preset
        }

        channel_info = self._sound_engine.channel_info(available_channel)

        logging.debug(
            f"Registered '{channel_info.name}' (bank={bank},preset={preset}) "
            f"for channel {available_channel} and mapped to '{instrument_name}'!"
        )

    def get_instrument(self, instrument_name):
        """Retrieve details of a registered instrument.

        Args:
            instrument_name (str): The name of the instrument to retrieve.

        Returns:
            dict: A dictionary containing the instrument's details, or None if not found.
        """
        return self._registry.get(instrument_name, None)

    def list_registered_instruments(self):
        """List all registered instruments.

        Returns:
            list: A list of registered instrument names.
        """
        return list(self._registry.keys())
