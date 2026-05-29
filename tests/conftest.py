import pytest
from pathlib import Path

@pytest.fixture(scope="session")
def hazard_curves_data():
    return Path(__file__).parent / "hazard_curves"

@pytest.fixture
def hazard_curves_input(hazard_curves_data):
    return hazard_curves_data / "input_data"

@pytest.fixture
def hazard_curves_matlab(hazard_curves_data):
    return hazard_curves_data / "matlab_data"

@pytest.fixture
def test_output_dir(tmp_path):
    """Provides a temporary directory for test outputs, cleaned up automatically."""
    return tmp_path / "test_output"
