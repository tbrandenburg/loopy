import fluidsynth

import logging
import threading

class StepSequencer:
    """Sequencer that plays its own step channels tick by tick"""

    def __init__(self, synth, bpm=120, steps=32, beats_per_measure=4):
        """Constructor"""
        self._synth = synth
        self._seq = fluidsynth.Sequencer(time_scale=1000, use_system_timer=False)
        self._synth_id = self._seq.register_fluidsynth(self._synth)
        self._step_callback_id = self._seq.register_client("stepCallback", self._step_callback)

        self._channels = []

        self._bpm = bpm
        self._beats_per_measure = beats_per_measure
        self._seconds_per_beat = 60 / bpm
        self._steps = steps
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