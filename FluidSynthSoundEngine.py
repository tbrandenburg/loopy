from ChannelInfo import ChannelInfo
from InstrumentRegistry import DRIVER
from SoundEngine import SoundEngine


import fluidsynth

import logging
import threading

PBQ = 1000

class FluidSynthSoundEngine(SoundEngine):
    """Concrete implementation of SoundEngine using FluidSynth."""

    def __init__(self, bpm=120, beats_per_measure=4):
        """Initialize the FluidSynth sound engine instance."""
        self._synth = fluidsynth.Synth()
        self._seq = fluidsynth.Sequencer(time_scale=1000, use_system_timer=False)
        self._synth_id = self._seq.register_fluidsynth(self._synth)
        self._step_callback_id = self._seq.register_client("stepCallback", self._step_callback)

        self._channels = []

        self._bpm = bpm
        self._beats_per_measure = beats_per_measure
        self._seconds_per_beat = 60 / bpm
        self._is_playing = False
        self._lock = threading.Lock()  # For synchronizing the tick steps

    def _step_callback(self, time, event, seq, data):
        # Increment current step
        self._cur_step = (self._cur_step + 1) % self._steps

        # Set new start_time if there was a step overrun
        if self._cur_step == 0:
            self._start_time = self._start_time + int(self._seconds_per_beat * 1000 * self._steps)
            # Calculate new note times
            self.update()

        # Set new beat callback
        self._seq.timer(self._start_time + int(self._seconds_per_beat * 1000 * (self._cur_step + 1)), dest=self._step_callback_id)

        logging.debug(f"Beat {self._cur_step} triggered: time={time}")

    def get_steps(self):
        return self._steps

    def add_channel(self, channel):
        """Adds a channel to the step sequencer."""
        self._channels.append(channel)

    def remove_channel(self, channel):
        """Removes a channel from the step sequencer."""
        self._channels.remove(channel)

    def get_channels(self):
        """Returns all step sequencer channels"""
        return self._channels

    def update(self):
        """Loads the notes of the step channels into the sequence"""
        for channel in self._channels:
            channel_steps = channel.get_steps()
            i = 0
            for step in channel_steps:
                if step:
                    start_tick = self._start_time + int(self._seconds_per_beat * 1000 * i)  # Calculates the start time of the step
                    note = step[0]                              # MIDI note value
                    velocity = step[1]                          # Note velocity

                    if note and velocity:
                        # Set Note-On event
                        self._seq.note_on(
                            start_tick,            # Time of the Note-On event
                            0,                     # MIDI channel (here channel 0, can be adjusted)
                            note,                  # MIDI note value
                            velocity,              # Note velocity
                            dest=self._synth_id    # Target Synthesizer ID
                        )

                        # Set Note-Off event (one beat later)
                        stop_tick = self._start_time + int(self._seconds_per_beat * 1000 * (i + 1))  # Calculates the stop time of the step
                        self._seq.note_off(
                            stop_tick,             # Time of the Note-Off event
                            0,                     # MIDI channel
                            note,                  # MIDI note value
                            80,                    # Velocity when releasing the note
                            dest=self._synth_id    # Target Synthesizer ID
                        )
                        logging.debug(f"  note_on({start_tick}, 0, {note}, 100), note_off({stop_tick} , 0, 80, 100)")
                i = i + 1

    def play(self):
        self._is_playing = True
        self._start_time = self._seq.get_tick()
        self._cur_step = 0
        self.update()
        self._seq.timer(self._seq.get_tick() + int(self._seconds_per_beat * 1000), dest=self._step_callback_id)

    def stop(self):
        self._is_playing = False

    def start(self):
        """Start the FluidSynth engine with the configured driver."""
        self._synth.start(driver=DRIVER)

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