"""
JPM (Joint Probability Method) pure computation pipeline.
Original MATLAB implementation: StormSim_JPM.m, StormSim_JPM_integration.m
Authors: N.C. Nadal-Caraballo, E. Ramos-Santiago (ERDC-CHL Coastal Hazards Group)
"""

from numpy.typing import NDArray

from .core import InputData, Options
from .engine import integrate, interpolate_results, preprocess


def compute(input_data: InputData, opts: Options) -> list[tuple[str, NDArray]]:
    """
    Pure JPM pipeline: preprocessing → integration → interpolation.

    Pipeline:
      1. Validate and filter input data (flag values, NaN/inf/non-positive).
      2. Apply ITCS Gaussian discretisation (444 replicates) to tile response
         and probability mass; apply first-partition uncertainty correction.
      3. Integrate tiled response against discrete storm weights to produce
         exceedance frequency curve; apply confidence limits.
      4. Interpolate onto standard log-spaced plot grid and discrete table grid.

    Parameters:
        input_data:  InputData wrapping the N × 4 array [timestamp, response, skew_tides, DSW]
                     plus optional flag_value and slc
        opts:        validated Options instance

    Returns:
        List of (name, array) pairs:
          "plot"   — shape (n_plt, 1 + n_prc), columns [AEF/AEP, Best, prc...]
          "table"  — shape (n_tbl, 1 + n_prc), same columns; only when return_table=True
    """
    resp, prob_mass = preprocess(input_data, opts)
    x, y = integrate(resp, prob_mass, opts)
    return interpolate_results(x, y, opts)
