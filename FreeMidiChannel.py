from InstrumentChannel import InstrumentChannel

import mido

import logging
import threading

class FreeMidiChannel(InstrumentChannel):
    """A channel for MIDI input and output with FluidSynth and polyphony."""

    def __init__(self, project, port_name, instrument_name, volume=80):
        super().__init__(project, instrument_name, volume)
        self._port_name = port_name
        self._active_notes = set()

    def play(self):
        """Starts the channel and begins receiving MIDI data."""
        super().play()  # Set the channel to "play"
        if self._is_playing:
            logging.debug(f"Begin receiving MIDI data on channel {self._instrument_name}...")
            threading.Thread(target=self._read_midi_input, daemon=True).start()

    def stop(self):
        """Stops the channel and ends all active notes."""
        super().stop()  # Set the channel to "stop"
        if not self._is_playing:
            logging.debug(f"Stopping MIDI data listening on channel {self._instrument_name}...")
            for note in self._active_notes:
                self._synth.noteoff(self._channel, note)
            self._active_notes.clear()

    def _play_midi_message(self, message):
        """Plays a MIDI message and manages active notes."""
        if message.type == "note_on" and message.velocity > 0:
            if message.note not in self._active_notes:
                logging.debug(f"Note on: {message.note}, Velocity: {message.velocity}")
                self._synth.synch_noteon(self._channel, message.note, message.velocity)
                self._active_notes.add(message.note)
        elif message.type in ["note_off", "note_on"] and message.velocity == 0:
            if message.note in self._active_notes:
                logging.debug(f"Note off: {message.note}")
                self._synth.synch_noteoff(self._channel, message.note)
                self._active_notes.remove(message.note)

    def _read_midi_input(self):
        """Reads MIDI inputs from a specific MIDI port and plays them."""
        with mido.open_input(self._port_name) as port:
            logging.debug(f"Listening for MIDI input on {self._port_name}...")
            for message in port:
                if self._is_playing:
                    self._play_midi_message(message)