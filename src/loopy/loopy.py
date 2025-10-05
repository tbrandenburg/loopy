import argparse
import curses
import logging
import threading
import time
from typing import List, Optional, Sequence

import mido

from .FreeMetronomeChannel import FreeMetronomeChannel
from .FreeMidiChannel import FreeMidiChannel
from .FluidSynthSoundEngine import FluidSynthSoundEngine
from .Project import Project
from .StepChannel import StepChannel
from .StepSequencerChannel import StepSequencerChannel
from .themes import get_theme, iter_themes

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def render_curses(screen, project, theme):
    """Curses render function for threading."""

    registry = project.get_instrument_registry()
    selected_index = 0
    instrument_menu_open = False
    instrument_menu_index = 0
    instrument_menu_page_size = 0
    instrument_menu_context = {}
    instrument_options: List = []
    status_message = ""
    status_expires = 0.0

    def update_status(message: str, duration: float = 3.0) -> None:
        nonlocal status_message, status_expires
        status_message = message
        status_expires = time.time() + duration

    try:
        curses.curs_set(0)
    except curses.error:
        pass

    try:
        screen.nodelay(True)
        screen.keypad(True)
        screen.timeout(150)
    except curses.error:
        pass

    try:
        colour_pairs = theme.apply(screen)
    except Exception:
        colour_pairs = {}

    try:
        while True:
            max_y, max_x = screen.getmaxyx()
            now = time.time()
            if status_message and now > status_expires:
                status_message = ""

            screen.erase()

            header = f"Loopy — {theme.display_name}"
            try:
                screen.addnstr(0, 0, header, max_x - 1, theme.style("title", colour_pairs))
            except curses.error:
                pass
            line = 2

            selectables = []
            channels = project.get_channels()
            for index, channel in enumerate(channels):
                if line >= max_y - 2:
                    break

                if hasattr(channel, "get_instrument_label"):
                    instrument_label = channel.get_instrument_label()
                elif hasattr(channel, "get_instrument_name"):
                    instrument_label = registry.get_instrument_display_name(channel.get_instrument_name())
                else:
                    instrument_label = str(channel)

                channel_index = len(selectables)
                selectables.append({"type": "channel", "target": channel})
                attr = theme.style("channel_label", colour_pairs)
                if channel_index == selected_index:
                    attr |= curses.A_REVERSE

                channel_label = f"Channel {index + 1}: {instrument_label}"
                try:
                    screen.addnstr(line, 0, channel_label, max_x - 1, attr)
                except curses.error:
                    pass
                line += 1

                if isinstance(channel, StepSequencerChannel):
                    sequencer = channel.get_sequencer()
                    step_channels = sequencer.get_channels()

                    for step_channel in step_channels:
                        if line >= max_y - 2:
                            break

                        step_index = len(selectables)
                        selectables.append({"type": "step_channel", "target": step_channel})
                        highlight = step_index == selected_index

                        step_label = registry.get_instrument_display_name(step_channel.get_instrument_name())
                        label_attr = theme.style("channel_label", colour_pairs)
                        if highlight:
                            label_attr |= curses.A_REVERSE
                        try:
                            screen.addnstr(line, 0, f"    {step_label}", max_x - 1, label_attr)
                        except curses.error:
                            pass

                        grid_attr = theme.style("grid", colour_pairs)
                        if highlight:
                            grid_attr |= curses.A_REVERSE

                        if max_x > 4:
                            try:
                                screen.addstr(line, 3, "[", grid_attr)
                            except curses.error:
                                pass

                            steps = step_channel.get_steps() or []
                            visible_steps = max(0, min(len(steps), (max_x - 6) // 2))
                            for j, step in enumerate(steps[:visible_steps]):
                                column = j * 2 + 4
                                token = "step_off"
                                glyph = "o-"
                                if step is not None:
                                    note, velocity = step
                                    if note is not None and velocity is not None:
                                        token = "step_on"
                                        glyph = "x-"
                                style = theme.style(token, colour_pairs)
                                if highlight:
                                    style |= curses.A_REVERSE
                                try:
                                    screen.addnstr(line, column, glyph, max_x - column - 1, style)
                                except curses.error:
                                    pass

                            closing_column = min(max_x - 2, 4 + visible_steps * 2)
                            try:
                                screen.addstr(line, closing_column, "]", grid_attr)
                            except curses.error:
                                pass

                        line += 1

            if selectables:
                selected_index = max(0, min(selected_index, len(selectables) - 1))
            else:
                selected_index = 0

            footer_attr = theme.style("meta", colour_pairs)
            footer_line = max_y - 1
            status_line = footer_line - 1

            if status_message and status_line >= 0:
                try:
                    screen.addnstr(status_line, 0, status_message, max_x - 1, footer_attr)
                except curses.error:
                    pass

            if instrument_menu_open:
                instruction = "↑/↓ Navigate · Enter Apply · Esc Cancel"
            else:
                instruction = "↑/↓ Select · i Change instrument"
            footer = f"Theme: {theme.display_name} ({theme.key}) | {instruction}"
            try:
                screen.addnstr(footer_line, 0, footer, max_x - 1, footer_attr)
            except curses.error:
                pass

            overlay_window = None
            instrument_menu_page_size = 0
            if instrument_menu_open and instrument_options:
                menu_height = min(max_y - 4, len(instrument_options) + 2)
                menu_height = max(menu_height, 3)
                menu_width = min(max_x - 4, max(len(option.display_name) for option in instrument_options) + 4)
                menu_width = max(menu_width, 32)
                start_y = max(1, (max_y - menu_height) // 2)
                start_x = max(1, (max_x - menu_width) // 2)

                try:
                    overlay_window = screen.subwin(menu_height, menu_width, start_y, start_x)
                    overlay_window.box()
                except curses.error:
                    overlay_window = None

                if overlay_window is not None:
                    instrument_menu_page_size = menu_height - 2
                    current_descriptor = instrument_menu_context.get("current_descriptor")
                    visible_rows = instrument_menu_page_size
                    scroll_offset = min(
                        max(0, instrument_menu_index - visible_rows + 1),
                        max(0, len(instrument_options) - visible_rows),
                    )

                    for row in range(visible_rows):
                        option_index = scroll_offset + row
                        if option_index >= len(instrument_options):
                            break
                        option = instrument_options[option_index]
                        prefix = "  "
                        if current_descriptor and option.soundfont_path == current_descriptor.get("soundfont_path") \
                                and option.bank == current_descriptor.get("bank") \
                                and option.preset == current_descriptor.get("preset"):
                            prefix = "→ "
                        text = f"{prefix}{option.display_name}"
                        attr = theme.style("channel_label", colour_pairs)
                        if option_index == instrument_menu_index:
                            attr |= curses.A_REVERSE
                        try:
                            overlay_window.addnstr(1 + row, 1, text, menu_width - 2, attr)
                        except curses.error:
                            pass

            screen.refresh()
            if overlay_window is not None:
                overlay_window.refresh()

            try:
                key = screen.getch()
            except curses.error:
                key = -1

            if key == curses.ERR or key == -1:
                continue

            if instrument_menu_open:
                if key in (curses.KEY_UP, ord("k")):
                    instrument_menu_index = max(0, instrument_menu_index - 1)
                elif key in (curses.KEY_DOWN, ord("j")):
                    instrument_menu_index = min(len(instrument_options) - 1, instrument_menu_index + 1)
                elif key == curses.KEY_PPAGE:
                    step = max(1, instrument_menu_page_size)
                    instrument_menu_index = max(0, instrument_menu_index - step)
                elif key == curses.KEY_NPAGE:
                    step = max(1, instrument_menu_page_size)
                    instrument_menu_index = min(len(instrument_options) - 1, instrument_menu_index + step)
                elif key in (curses.KEY_ENTER, 10, 13):
                    if 0 <= instrument_menu_index < len(instrument_options):
                        option = instrument_options[instrument_menu_index]
                        try:
                            registry.register_instrument(
                                option.alias,
                                option.soundfont_path,
                                option.bank,
                                option.preset,
                            )
                            target = instrument_menu_context.get("target")
                            if target:
                                target_obj = target.get("target")
                                if hasattr(target_obj, "set_instrument"):
                                    target_obj.set_instrument(option.alias)
                            update_status(f"Instrument set to {option.display_name}", 4.0)
                        except Exception as error:  # pragma: no cover - defensive logging
                            update_status(f"Failed to select instrument: {error}", 6.0)
                        instrument_menu_open = False
                elif key in (27, ord("q")):
                    instrument_menu_open = False
                    update_status("Cancelled instrument selection", 2.0)
            else:
                if key in (curses.KEY_UP, ord("k")):
                    if selectables:
                        selected_index = max(0, selected_index - 1)
                elif key in (curses.KEY_DOWN, ord("j")):
                    if selectables:
                        selected_index = min(len(selectables) - 1, selected_index + 1)
                elif key == ord("i"):
                    if not selectables:
                        update_status("No channels available", 2.0)
                        continue

                    instrument_options = registry.list_available_instruments()
                    if not instrument_options:
                        update_status("No instruments available", 3.0)
                        continue

                    target = selectables[selected_index]
                    instrument_menu_context = {"target": target}

                    descriptor = None
                    target_obj = target.get("target")
                    if hasattr(target_obj, "get_instrument_name"):
                        descriptor = registry.get_instrument_descriptor(target_obj.get_instrument_name())
                    instrument_menu_context["current_descriptor"] = descriptor

                    instrument_menu_index = 0
                    if descriptor:
                        for idx, option in enumerate(instrument_options):
                            if (
                                option.soundfont_path == descriptor.get("soundfont_path")
                                and option.bank == descriptor.get("bank")
                                and option.preset == descriptor.get("preset")
                            ):
                                instrument_menu_index = idx
                                break

                    instrument_menu_open = True
                elif key in (ord("q"), ord("Q")):
                    update_status("Press Ctrl+C to exit.", 2.0)

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

    project.get_sequencer().add_channel(step_channel_1)

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