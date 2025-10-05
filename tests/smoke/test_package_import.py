import importlib


def test_loopy_package_importable():
    module = importlib.import_module("loopy")
    assert hasattr(module, "Project")
    assert hasattr(module, "StepSequencer")
