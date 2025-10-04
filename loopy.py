import argparse
import curses
import logging
import threading
import time
from typing import Optional, Sequence

import mido

from FreeMetronomeChannel import FreeMetronomeChannel
from FreeMidiChannel import FreeMidiChannel
from FluidSynthSoundEngine import FluidSynthSoundEngine
from Project import Project
from StepChannel import StepChannel
from StepSequencerChannel import StepSequencerChannel
from themes import get_theme, iter_themes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def render_curses(screen, project, theme):
    """Curses render function for threading."""
    try:
        colour_pairs = theme.apply(screen)
        while True:
            screen.erase()
            max_y, _ = screen.getmaxyx()
            line = 0

            header = f"Loopy — {theme.display_name}"
            screen.addstr(line, 0, header, theme.style("title", colour_pairs))
            line += 2

            for i, channel in enumerate(project.get_channels()):
                if line >= max_y - 1:
                    break

                channel_label = f"Channel {i + 1}: {channel._instrument_name}"
                screen.addstr(line, 0, channel_label, theme.style("channel_label", colour_pairs))

                if isinstance(channel, StepSequencerChannel):
                    sequencer = channel.get_sequencer()
                    step_channels = sequencer.get_channels()

                    for step_channel in step_channels:
                        line += 1
                        if line >= max_y - 1:
                            break

                        screen.addstr(line, 3, "[", theme.style("grid", colour_pairs))
                        for j, step in enumerate(step_channel.get_steps()):
                            column = j * 2 + 4
                            token = "step_off"
                            glyph = "o-"
                            if step is not None:
                                note, velocity = step
                                if note is not None and velocity is not None:
                                    token = "step_on"
                                    glyph = "x-"
                            screen.addstr(line, column, glyph, theme.style(token, colour_pairs))
                        screen.addstr(line, 67, "]", theme.style("grid", colour_pairs))

                line += 1

            footer_line = max_y - 1
            footer = f"Theme: {theme.display_name} ({theme.key})"
            screen.addstr(footer_line, 0, footer, theme.style("meta", colour_pairs))

            screen.refresh()
            time.sleep(0.5)
    except curses.error:
        pass
    except Exception as error:  # pragma: no cover - defensive logging for curses thread
        logging.error("Unexpected error happened: %s", error)
        try:
            screen.addstr(10, 0, f"!!! Unexpected error happened: {error} !!!")
            screen.refresh()
            time.sleep(10)
        except curses.error:
            pass


def start_curses_thread(project, theme):
    def curses_thread(screen):
        render_curses(screen, project, theme)

    threading.Thread(target=curses.wrapper, args=(curses_thread,), daemon=True).start()


def build_project() -> Project:
    fs_sound_engine = FluidSynthSoundEngine()
    project = Project(fs_sound_engine, bpm=120, beats_per_measure=4)

    registry = project.get_instrument_registry()
    registry.register_instrument("Piano", "sf2/GeneralUser-GS.sf2", 0, 0)
    registry.register_instrument("Jazz Guitar", "sf2/GeneralUser-GS.sf2", 0, 26)
    registry.register_instrument("Metronome", "sf2/GeneralUser-GS.sf2", 0, 115)

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

    fs_sound_engine.add_channel(step_channel_1)

    for port_name in mido.get_input_names():
        fluid_midi_channel = FreeMidiChannel(project, port_name, "Piano")
        project.add_channel(fluid_midi_channel)

    metronome_channel = FreeMetronomeChannel(project, "Metronome")
    project.add_channel(metronome_channel)

    step_sequencer_channel = StepSequencerChannel(project, "Step Sequencer")
    project.add_channel(step_sequencer_channel)

    return project


def parse_arguments(argv: Optional[Sequence[str]] = None):
    parser = argparse.ArgumentParser(description="Loopy MIDI sequencer")
    parser.add_argument(
        "--theme",
        default="tokyo-night",
        choices=[theme.key for theme in iter_themes()],
        help="Select the colour theme for the interface.",
    )
    parser.add_argument(
        "--list-themes",
        action="store_true",
        help="List available themes and exit.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_arguments(argv)

    if args.list_themes:
        for theme in iter_themes():
            print(f"{theme.key}: {theme.display_name} — {theme.description}")
        return

    try:
        theme = get_theme(args.theme)
    except KeyError as error:
        logging.error(error)
        return

    project = build_project()
    start_curses_thread(project, theme)

    project.play()
    time.sleep(20)
    project.stop()


if __name__ == "__main__":
    main()

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