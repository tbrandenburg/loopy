# loopy

Python based MIDI sequencer and looper.

## Architecture overview

```mermaid
flowchart LR
    Project[Project] -->|controls tempo| Metronome[Metronome]
    Project -->|starts| SoundEngine
    Project -->|manages| InstrumentChannels[Instrument Channels]

    SoundEngine -->|loads presets| SoundBank[(Sound Bank / SoundFonts)]
    SoundBank -->|provides voices| MIDI[FluidSynth / MIDI Engine]
    InstrumentRegistry[Instrument Registry] -->|assigns channel + program| SoundEngine
    Project -->|owns| InstrumentRegistry

    InstrumentChannels --> StepSequencerChannel
    StepSequencerChannel --> Sequence[Sequence]
    Sequence --> Step[Steps]
    Step -->|trigger note| SoundEngine

    InstrumentChannels --> FreeMidiChannel
    InstrumentChannels --> FreeMetronomeChannel

    SoundEngine -->|mixes| Output[Audio Output]
```

## Running with uv

This project is distributed as a module rather than a console script, so
`uv run loopy` will not find an entry point. Use Python's module launcher
instead:

```bash
uv run -- python -m loopy.loopy
```

You can pass all of the usual CLI flags, for example:

```bash
uv run -- python -m loopy.loopy --theme lofi-chill
uv run -- python -m loopy.loopy --list-themes
```

> [!NOTE]
> On Linux you need the ALSA development headers so that the optional
> `pyalsaaudio` dependency can compile. Install them before running `uv run`:
>
> ```bash
> sudo apt-get install libasound2-dev
> ```

## Interface themes

Loopy now supports selectable colour themes for its curses interface. Run the
application with the `--theme` flag to pick the LoFi chilly look or fall back to
the classic console palette:

```bash
python loopy.py --theme lofi-chill
```

To see the available themes and their descriptions, use:

```bash
python loopy.py --list-themes
```
