import mido
import threading
import curses
import time
import sys
import logging
import traceback

from FreeMetronomeChannel import FreeMetronomeChannel
from FreeMidiChannel import FreeMidiChannel
from FluidSynthSoundEngine import FluidSynthSoundEngine
from Project import Project
from StepChannel import StepChannel
from StepSequencerChannel import StepSequencerChannel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

# Create a FluidSynth sound engine instance
fs_sound_engine = FluidSynthSoundEngine()

# Project with BPM=120 and 4 beats per measure
project = Project(fs_sound_engine, bpm=120, beats_per_measure=4)

# Register instruments
project.get_instrument_registry().register_instrument("Piano", "sf2/GeneralUser-GS.sf2", 0, 0)
project.get_instrument_registry().register_instrument("Jazz Guitar", "sf2/GeneralUser-GS.sf2", 0, 26)
project.get_instrument_registry().register_instrument("Metronome", "sf2/GeneralUser-GS.sf2", 0, 115)

# Create Step Channel
step_channel_1 = StepChannel("Jazz Guitar")
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
fs_sound_engine.add_channel(step_channel_1)

# Create Instrument Channels
for port_name in mido.get_input_names():
    fluid_midi_channel = FreeMidiChannel(project, port_name, "Piano")
    project.add_channel(fluid_midi_channel)

metronome_channel = FreeMetronomeChannel(project, "Metronome")
project.add_channel(metronome_channel)

step_sequencer_channel = StepSequencerChannel(project, "Step Sequencer")
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
# - Working stop functionality

# - Refactor instrument registry place
# - Refactor instrument channel and soundengine selection
# - Proper SoundEngine base class
# - get_sequencer bei StepSequencerChannel?
# - soundengine.play() ? 
# - self._steps = 32 ?