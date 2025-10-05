from loopy.StepChannel import StepChannel


def test_set_and_reset_step_extends_pattern():
    channel = StepChannel("bass")

    channel.set_step(3, 48, 80)
    assert channel.get_steps() == [None, None, None, [48, 80]]

    channel.reset_step(1)
    assert channel.get_steps() == [None, None, None, [48, 80]]

    channel.reset_step(3)
    assert channel.get_steps()[3] is None
