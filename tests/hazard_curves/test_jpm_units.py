import pytest
import numpy as np
import pandas as pd
from stormsim.hazard_curves.jpm.engine import preprocess, integrate
from stormsim.hazard_curves.jpm.core import InputData, Options, IntegrationEnum, UncertaintyEnum


@pytest.fixture
def base_options():
    return Options(integration_mode=IntegrationEnum.ATCS, uncertainty_mode=UncertaintyEnum.ABSOLUTE, ua=0.1)


def test_preprocess_empty_data(base_options):
    data = np.array([[]])
    with pytest.raises(RuntimeError, match="Input data must be at least 2D"):
        preprocess(InputData(data=data), base_options)


def test_preprocess_negative_values(base_options):
    data = np.array([[1.0, -1.0, 0.5, 0.1], [1.0, -2.0, 0.5, 0.1]])
    with pytest.raises(RuntimeError, match="Invalid response removal"):
        preprocess(InputData(data=data), base_options)


def test_integrate_basic():
    resp = np.array([10.0, 5.0, 1.0])
    prob = np.array([0.2, 0.3, 0.5])
    opts = Options(uncertainty_mode=UncertaintyEnum.ABSOLUTE, ua=0.1, tide_std=0.0)
    x, y = integrate(resp, prob, opts)

    assert y.shape[1] == 5
    assert len(x) == 3
