"""
JPM (Joint Probability Method) pure computation pipeline.
Original MATLAB implementation: StormSim_JPM.m, StormSim_JPM_integration.m
Authors: N.C. Nadal-Caraballo, E. Ramos-Santiago (ERDC-CHL Coastal Hazards Group)
"""

from numpy.typing import NDArray

from .core import Options
from .engine import integrate, interpolate_results, preprocess


def compute(data: NDArray, opts: Options) -> list[tuple[str, NDArray]]:
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
        data:  N × 4 array with columns [timestamp, response, skew_tides, DSW]
        opts:  validated Options instance

    Returns:
        List of (name, array) pairs:
          "plot"   — shape (n_plt, 1 + n_prc), columns [AEF/AEP, Best, prc...]
          "table"  — shape (n_tbl, 1 + n_prc), same columns; only when return_table=True
    """
    resp, prob_mass = preprocess(data, opts)
    x, y = integrate(resp, prob_mass, opts)
    return interpolate_results(x, y, opts)
