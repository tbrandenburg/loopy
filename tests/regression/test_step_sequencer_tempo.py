import pytest

from loopy.StepSequencer import StepSequencer


def test_advance_one_step_returns_current_step_duration(instrument_registry):
    sequencer = StepSequencer(instrument_registry, steps=2, bpm=120)

    assert sequencer.advance_one_step() == pytest.approx(0.5)

    sequencer.set_tempo(60)
    assert sequencer.advance_one_step() == pytest.approx(1.0)
