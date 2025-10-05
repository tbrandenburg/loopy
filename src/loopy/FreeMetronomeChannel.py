from .InstrumentChannel import InstrumentChannel

import threading

class FreeMetronomeChannel(InstrumentChannel):
    """A channel for the metronome, which plays only one note on each tick, with accent logic."""

    def __init__(self, project, instrument_name, volume=100, accent_volume=127):
        super().__init__(project, instrument_name, volume)
        self._accent_volume = accent_volume  # Volume of the accent on the first beat
        self._tick_count = 0  # Counter for the beat count
        self._noteoff_timer = None
        self._active_note = None

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

            self._cancel_pending_release()
            self._active_note = note
            self._synth.synch_noteon(self._channel, note, velocity)

            duration = self._parent.get_seconds_per_beat()
            self._noteoff_timer = threading.Timer(duration, self._release_note, args=(note,))
            self._noteoff_timer.daemon = True
            self._noteoff_timer.start()

    def stop(self):
        """Stops the channel and cancels any pending note off."""
        self._cancel_pending_release()
        self._tick_count = 0
        super().stop()

    def _release_note(self, note):
        if self._active_note == note:
            self._synth.synch_noteoff(self._channel, note)
            self._active_note = None
            self._noteoff_timer = None

    def _cancel_pending_release(self):
        if self._noteoff_timer is not None:
            self._noteoff_timer.cancel()
            self._noteoff_timer = None
        if self._active_note is not None:
            self._synth.synch_noteoff(self._channel, self._active_note)
            self._active_note = None