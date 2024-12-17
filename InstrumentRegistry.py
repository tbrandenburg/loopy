import fluidsynth
import sys
import logging

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
    """Manages instrument IDs and maps them to FluidSynth soundfonts."""

    def __init__(self, project):
        self._registry = {}  # Stores information about instruments and their synth instances
        self._soundfont_cache = {}  # Caches loaded soundfonts (path -> sfid)
        self._fs = fluidsynth.Synth()
        self._fs.start(driver=DRIVER)  # Starts FluidSynth with the appropriate driver

    def get_synth(self):
        return self._fs

    def register_instrument(self, instrument_name, soundfont_path, bank=0, preset=0):
        """Registers an instrument with a soundfont and creates the synth instance."""

        # Check if the soundfont is already loaded
        if soundfont_path in self._soundfont_cache:
            sfid = self._soundfont_cache[soundfont_path]  # Use the existing sfid
        else:
            sfid = self._fs.sfload(soundfont_path)  # Load the soundfont
            self._soundfont_cache[soundfont_path] = sfid  # Save sfid in cache

        # Select the instrument (program) on a new channel
        # Find the next free channel
        available_channel = len(self._registry) % 16  # Simple round-robin approach

        # Select the program and register it
        self._fs.program_select(available_channel, sfid, bank, preset)
        self._registry[instrument_name] = {
            "channel": available_channel,
            "sfid": sfid,
            "bank": bank,
            "preset": preset
        }

        channel_info = self._fs.channel_info(available_channel)

        logging.debug(f"Registered '{channel_info[3]}' (bank={bank},preset={preset}) for FluidSynth channel {available_channel} and mapped to '{instrument_name}'!")

    def get_instrument(self, instrument_name):
        """Returns the FluidSynth instance and the instrument's channel."""
        instrument = self._registry.get(instrument_name)
        if instrument:
            return self._fs, instrument["channel"]
        return None, None

    def list_registered_instruments(self):
        """Returns a list of all registered instruments."""
        return list(self._registry.keys())