from InstrumentChannel import InstrumentChannel

import time

class FreeMetronomeChannel(InstrumentChannel):
    """A channel for the metronome, which plays only one note on each tick, with accent logic."""

    def __init__(self, project, instrument_name, volume=100, accent_volume=127):
        super().__init__(project, instrument_name, volume)
        self._accent_volume = accent_volume  # Volume of the accent on the first beat
        self._tick_count = 0  # Counter for the beat count

    def tick(self):
        """Responds to the tick and plays a note with accent logic."""
        if self._is_playing:
            # Determine if this is the first beat of a measure
            self._tick_count = (self._tick_count % self._parent.get_beats_per_measure()) + 1

            if self._tick_count == 1:
                # Accent on the first beat of the measure (louder)
                note = 60  # Example note for the beat (can be changed)
                velocity = int(self._accent_volume * self._volume / 100)  # Volume of the accent
            else:
                # Normal volume for other beats
                note = 60  # Example note for the beat
                velocity = self.get_volume()  # Normal volume

            # Play the note for the duration of seconds_per_beat
            self._synth.noteon(self._channel, note, velocity)
            time.sleep(self._parent.get_seconds_per_beat())  # The duration of the note matches the length of a beat
            self._synth.noteoff(self._channel, note)