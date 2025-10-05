from loopy.StepChannel import StepChannel
from loopy.StepSequencer import StepSequencer


def test_step_sequencer_triggers_notes(instrument_registry, fake_sound_engine):
    instrument_registry.register_instrument("piano", "tests/data/Dummy.sf2", bank=0, preset=0)

    sequencer = StepSequencer(instrument_registry, steps=4, bpm=120)
    channel = StepChannel("piano", volume=90)
    channel.set_step(0, 60, 100)
    channel.set_step(1, None, None)
    channel.set_step(2, 62, None)
    channel.set_step(3, 64, 70)

    sequencer.add_channel(channel)

    for _ in range(4):
        sequencer.advance_one_step()

    assert fake_sound_engine.note_events[:5] == [
        ("on", 0, 60, 100),
        ("off", 0, 60, None),
        ("on", 0, 62, 90),
        ("off", 0, 62, None),
        ("on", 0, 64, 70),
    ]
