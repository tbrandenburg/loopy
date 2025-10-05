import logging
import sys
import threading
from collections import deque

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

    def __init__(self, sound_engine: SoundEngine, max_channels: int = 16):
        """Initialize the instrument registry with a sound engine.

        Args:
            sound_engine (SoundEngine): The sound engine to use for managing instruments.
        """
        self._registry = {}  # Stores information about instruments and their channels
        self._soundfont_cache = {}  # Caches loaded soundfonts (path -> sfid)
        self._sound_engine = sound_engine
        self._available_channels = deque(range(max_channels))
        self._lock = threading.Lock()

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

        with self._lock:
            if instrument_name in self._registry:
                logging.debug("Instrument '%s' already registered.", instrument_name)
                return self._registry[instrument_name]["channel"]

            if not self._available_channels:
                raise RuntimeError("No MIDI channels available for new instruments.")

            available_channel = self._available_channels.popleft()

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

            return available_channel

    def get_instrument(self, instrument_name):
        """Returns the SoundEngine instance and the instrument's channel.

        Args:
            instrument_name (str): The name of the instrument to retrieve.

        Returns:
            list: A list containing the SoundEngine and the instrument channel
        """
        instrument = self._registry.get(instrument_name)
        if instrument:
            return self._sound_engine, instrument["channel"]
        return None, None

    def unregister_instrument(self, instrument_name):
        """Remove an instrument and release its MIDI channel."""
        with self._lock:
            instrument = self._registry.pop(instrument_name, None)
            if instrument is not None:
                self._available_channels.append(instrument["channel"])

    def get_sound_engine(self):
        """Expose the underlying sound engine."""
        return self._sound_engine

    def list_registered_instruments(self):
        """List all registered instruments.

        Returns:
            list: A list of registered instrument names.
        """
        return list(self._registry.keys())
