import mido
import threading
import curses
import time
import fluidsynth
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

class InstrumentChannel:
    """Abstract base class for all instrument channels."""
    
    def __init__(self, parent, instrument_name, volume=80):
        self._parent = parent
        self._volume = volume
        self._instrument_registry = parent.get_instrument_registry()
        self.set_instrument(instrument_name)
        self._is_playing = False

    def set_instrument(self, instrument_name):
        """Sets the channel's instrument based on the instrument name."""
        self._instrument_name = instrument_name
        self._synth, self._channel = self._instrument_registry.get_instrument(instrument_name)

    def set_volume(self, volume):
        """Sets the channel's volume."""
        self._volume = volume

    def get_volume(self):
        """Returns the channel's volume."""
        return self._volume
    
    def get_parent(self):
        """Returns parent"""
        return self._parent

    def play(self):
        """Starts the channel."""
        if not self._is_playing:
            logging.debug(f"Starting channel '{self}'...")
            self._is_playing = True

    def stop(self):
        """Stops the channel."""
        if self._is_playing:
            logging.debug(f"Pausing channel '{self}'...")
            self._is_playing = False

    def tick(self):
        """Reaction on tick step"""
        pass

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
                self._synth.noteon(self._channel, message.note, message.velocity)
                self._active_notes.add(message.note)
        elif message.type in ["note_off", "note_on"] and message.velocity == 0:
            if message.note in self._active_notes:
                logging.debug(f"Note off: {message.note}")
                self._synth.noteoff(self._channel, message.note)
                self._active_notes.remove(message.note)

    def _read_midi_input(self):
        """Reads MIDI inputs from a specific MIDI port and plays them."""
        with mido.open_input(self._port_name) as port:
            logging.debug(f"Listening for MIDI input on {self._port_name}...")
            for message in port:
                if self._is_playing:
                    self._play_midi_message(message)

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

class StepSequencerChannel(InstrumentChannel):
    """A channel for a step sequencer."""
    
    def __init__(self, project, sequencer, name, volume=80):
        super().__init__(project, name, volume)
        self._sequencer = sequencer

    def get_sequencer(self):
        """Returns sequencer"""
        return self._sequencer

    def play(self):
        """Starts the channel"""
        super().play()  # Set the channel to "play"
        if self._is_playing:
            self._sequencer.play()

    def stop(self):
        """Stops the channel"""
        super().stop()  # Set the channel to "stop"
        if not self._is_playing:
            self._sequencer.stop()

class StepChannel:
    """Abstract base class for all step channels."""
    
    def __init__(self, parent, instrument_name, volume=80):
        self._sequencer = parent
        self._instrument_name = instrument_name
        self._volume = volume
        self._is_playing = False
        self._steps = [None] * self._sequencer.get_steps()

    def set_step(self, step, note, velocity):
        # If the step index is greater than the current list, extend the list with None
        if step >= len(self._steps):
            # Add the required number of None values to reach the index
            self._steps.extend([None] * (step + 1 - len(self._steps)))
        
        # Set the step with the note and velocity
        self._steps[step] = [note, velocity]

    def reset_step(self, step):
        # If the step index is greater than the current list, extend the list with None
        if step >= len(self._steps):
            # Add the required number of None values to reach the index
            self._steps.extend([None] * (step + 1 - len(self._steps)))
        
        # Reset the step by setting it to None
        self._steps[step] = None

    def set_instrument(self, instrument_name):
        """Sets the channel's instrument based on the instrument name."""
        self._instrument_name = instrument_name

    def set_volume(self, volume):
        """Sets the channel's volume."""
        self._volume = volume

    def get_volume(self):
        """Returns the channel's volume."""
        return self._volume

    def play(self):
        """Starts the channel."""
        if not self._is_playing:
            logging.debug(f"Starting Step Channel {self._instrument_name}...")
            self._is_playing = True

    def stop(self):
        """Stops the channel."""
        if self._is_playing:
            logging.debug(f"Pausing Step Channel {self._instrument_name}...")
            self._is_playing = False

    def get_steps(self):
        return self._steps

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

class Project:
    """The project that manages the beat logic and controls channels."""
    
    def __init__(self, bpm=120, beats_per_measure=4):
        self._instrument_registry = InstrumentRegistry(self)  # Reference to the InstrumentRegistry
        self._bpm = bpm
        self._beats_per_measure = beats_per_measure
        self._seconds_per_beat = 60 / bpm  # Calculate seconds per beat (for the metronome)
        self._channels = []
        self._is_playing = False
        self._lock = threading.Lock()  # For synchronizing the tick steps

    def get_instrument_registry(self):
        """Returns the Instrument Registry."""
        return self._instrument_registry

    def get_bpm(self):
        """Returns the project's BPM."""
        return self._bpm

    def get_beats_per_measure(self):
        """Returns the project's beats per measure."""
        return self._beats_per_measure

    def get_seconds_per_beat(self):
        """Returns the seconds per beat based on the BPM."""
        return self._seconds_per_beat

    def add_channel(self, channel):
        """Adds a channel to the project."""
        self._channels.append(channel)

    def remove_channel(self, channel):
        """Removes a channel from the project."""
        self._channels.remove(channel)

    def get_channels(self):
        """Returns all channels"""
        return self._channels

    def start_ticking(self):
        """Starts the beat management and notifies all channels."""
        self._is_playing = True
        while self._is_playing:
            with self._lock:
                for tick in range(self._beats_per_measure):
                    # Notify all channels that a tick has occurred
                    for channel in self._channels:
                        channel.tick()
                    time.sleep(self.get_seconds_per_beat())  # Wait until the next beat

    def play(self):
        """Starts the project and all channels."""
        logging.debug("Starting the project.")
        threading.Thread(target=self.start_ticking).start()
        for channel in self._channels:
            logging.debug("Starting channel: %s", channel)
            channel.play()

    def stop(self):
        """Stops the project and all channels."""
        logging.debug("Stopping the project.")
        self._is_playing = False
        for channel in self._channels:
            logging.debug("Stopping channel: %s", channel)
            channel.stop()

def render_curses(screen, project):
    """Curses render function for threading"""
    try:
        while True:
            screen.clear()
            line = 0
            for i, channel in enumerate(project.get_channels()):
                # Show channel name
                screen.addstr(line, 0, f"Channel {i + 1}: {channel._instrument_name}")
                if isinstance(channel, StepSequencerChannel):
                    # Get parent sequencer
                    sequencer = channel.get_sequencer()

                    # Get children step channels
                    step_channels = sequencer.get_channels()

                    # Show steps
                    for step_channel in step_channels:
                        line=line+1
                        screen.addstr(line, 3, "[")
                        for j, step in enumerate(step_channel.get_steps()):
                            if step is None:
                                # Show non set steps
                                screen.addstr(line, j * 2 + 4, "o-")
                            else:
                                # Show set steps
                                note, velocity = step
                                if note is None or velocity is None:
                                    screen.addstr(line, j * 2 + 4, "o-")
                                else:
                                    screen.addstr(line, j * 2 + 4, "x-")
                        screen.addstr(line, 67, "]")
                line=line+1
            screen.refresh()  # Refresh screen
            time.sleep(0.5)   # Refresh rate
    except curses.error:
        pass  # Ignore display errors
    except Exception as e:
        # Handle all other exceptions
        logging.error(f"Unexpected error happened: {e}")
        screen.addstr(10, 0, f"!!! Unexpected error happened: {e} !!!")
        screen.refresh()
        time.sleep(10)  


def start_curses_thread(project):
    def curses_thread(screen):
        render_curses(screen, project)
    threading.Thread(target=curses.wrapper, args=(curses_thread,), daemon=True).start()

# Example Usage:

# Project with BPM=120 and 4 beats per measure
project = Project(bpm=120, beats_per_measure=4)

# Register instruments
project.get_instrument_registry().register_instrument("Piano", "sf2/GeneralUser-GS.sf2", 0, 0)
project.get_instrument_registry().register_instrument("Jazz Guitar", "sf2/GeneralUser-GS.sf2", 0, 26)
project.get_instrument_registry().register_instrument("Metronome", "sf2/GeneralUser-GS.sf2", 0, 115)

# Create Step Sequencer
step_sequencer = StepSequencer(project.get_instrument_registry().get_synth(), project.get_bpm(), 32, project.get_beats_per_measure())

# Create Step Channel
step_channel_1 = StepChannel(step_sequencer, "Jazz Guitar")
step_channel_1.set_step(0, 60, 127)
step_channel_1.set_step(1, 61, 127)
step_channel_1.set_step(2, 62, 127)
step_channel_1.set_step(3, 63, 127)
step_channel_1.set_step(4, 64, 127)
step_channel_1.set_step(5, 63, 127)
step_channel_1.set_step(6, 62, 127)
step_channel_1.set_step(7, 61, 127)
step_channel_1.set_step(8, 60, 127)
step_channel_1.set_step(17, 61, 127)
step_channel_1.set_step(18, 62, 127)
step_channel_1.set_step(19, 63, 127)
step_channel_1.set_step(20, 64, 127)
step_channel_1.set_step(21, 63, 127)
step_channel_1.set_step(22, 62, 127)
step_channel_1.set_step(23, 61, 127)
step_channel_1.set_step(24, 60, 127)

# Assign Step Channels
step_sequencer.add_channel(step_channel_1)

# Create Instrument Channels
for port_name in mido.get_input_names():
    fluid_midi_channel = FreeMidiChannel(project, port_name, "Piano")
    project.add_channel(fluid_midi_channel)

metronome_channel = FreeMetronomeChannel(project, "Metronome")
project.add_channel(metronome_channel)

step_sequencer_channel = StepSequencerChannel(project, step_sequencer, "Step Sequencer")
project.add_channel(step_sequencer_channel)

# Start curses display
start_curses_thread(project)

# Start the project
project.play()

# Stop the project after a while (20 seconds)
time.sleep(20)
project.stop()

# TODO
# - Correct Step-Channel MIDI channel
# - Volume Step-Channel MIDI channel
# - Polyphonic Step-Channel MIDI channel
# - Cool display
# - Working stop functionality