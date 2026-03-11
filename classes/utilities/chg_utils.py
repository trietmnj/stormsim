import numpy as np
from numpy.typing import NDArray
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Sequence

# ==========================================
# 1. Storm Selection
# ==========================================
def xc_storm_selection(
    response_vector_aef: NDArray[np.floating],
    response_vector: NDArray[np.floating],
    storm_id: NDArray[np.integer],
    num_storms: int = 20
) -> NDArray[np.floating]:
    """
    Select storms based on evenly spaced AEF targets.

    Parameters
    ----------
    response_vector_aef : np.ndarray
        Interpolated AEF values for each storm.
    response_vector : np.ndarray
        Response magnitudes (e.g., surge values).
    storm_id : np.ndarray
        Storm identifiers.
    num_storms : int
        Number of storms to select.

    Returns
    -------
    np.ndarray
        Array of shape (num_storms, 4) with columns:
        [target AEF, actual AEF, response, storm ID]
    """
    # Sort Response Vector
    idx = np.argsort(response_vector)[::-1]

    # AEF sampling range from data
    aef_min = float(np.min(response_vector_aef))
    aef_max = float(np.max(response_vector_aef))

    # Evenly spaced AEF targets
    aefs = np.linspace(aef_min, aef_max, num_storms)

    # Output: [target AEF, actual AEF, response, storm ID]
    storms_select = np.full((num_storms, 4), np.nan)

    # Work on copies so original arrays remain unchanged
    aef = response_vector_aef[idx]
    resp = response_vector[idx]
    sid = storm_id[idx]

    for i, target in enumerate(aefs):

        # First or last AEF → try exact match
        if i == 0 or i == len(aefs) - 1:
            ix = np.where(aef == target)[0]
            if len(ix) == 0:
                # fallback: closest AEF
                ix = [np.argmin(np.abs(aef - target))]
        else:
            diff = target - aef
            valid = np.where(diff >= 0)[0]

            if len(valid) == 0:
                # fallback: closest AEF above target
                ix = [np.argmin(np.abs(aef - target))]
            else:
                best = valid[np.argmin(diff[valid])]
                ix = [best]

        j = ix[0]

        storms_select[i, :] = np.array([target, aef[j], resp[j], sid[j]])

        # Remove selected storm from all vectors
        aef = np.delete(aef, j)
        resp = np.delete(resp, j)
        sid = np.delete(sid, j)

    return storms_select

# ==========================================
# 2. AEF Calculation
# ==========================================
def get_aef(
    storm_id: NDArray[np.integer],
    response_vector: NDArray[np.floating],
    benchmark_aef: NDArray[np.floating],
    benchmark_hc: NDArray[np.floating],
    dsw: Optional[NDArray[np.floating]] = None
):
    ...
    """Find associated AEF value to provided event responses."""
     # Treat empty arrays as None
    if isinstance(dsw, np.ndarray) and dsw.size == 0:
        dsw = None

    # Validate shape if dsw is provided
    if dsw is not None:
        if dsw.shape != response_vector.shape:
            raise ValueError(
                f"dsw must have shape {response_vector.shape}, "
                f"but got {dsw.shape}"
            )

    # Sort Response Vector
    idx = np.argsort(response_vector)[::-1]

    # Execute AEF Estimation According To Storm Type
    if dsw is None:
        # Apply Sorting
        resp_sorted = response_vector[idx]
        storm_id_sorted = storm_id[idx]
        # Interpolate log(AEF) at sorted responses
        x = benchmark_hc                         # MATLAB 4:end → Python 3:
        y = np.log(benchmark_aef)               # log(AEF)
        vq = np.interp(resp_sorted, x, y)     # interpolate in log-space
        # Report AEF Out With Original Sorting
        aef_out = np.exp(vq)
    else: # Process TC Storm Suite
        # Apply Sorting
        y = response_vector[idx]
        storm_id_sorted = storm_id[idx]
        # Compute AEF From DSWs
        x_aef = np.cumsum(dsw[idx])
        # Remove infinities
        mask = np.isfinite(np.log(x_aef))
        y = y[mask]
        x_aef = x_aef[mask]
        # Get Log Of AEF
        lx = np.log(x_aef)
        # Unique values
        _, ia_x = np.unique(lx, return_index=True)
        # Apply Mask And Revert To AEF 
        resp_sorted=y[ia_x]
        storm_id_sorted = storm_id_sorted[ia_x]
        aef_out=np.exp(lx[ia_x])

        # Build AEF Table 
        data_out = {
            "storm_id": storm_id_sorted,
            "aef": aef_out,
            "response": resp_sorted
        }
    # Return Values 
    return data_out

def prep_frequency():
    """
    Generates the Annual Exceedance Frequency (AEF) vectors for plotting and tables.
    Matches the original logic: 10^1 down to 10^-6.
    """
    # Create the plotting vector (plt_aef)
    d = 1.0/90.0
    v_exponents = np.arange(1, 0 - d/2, -d) 
    v = 10.0 ** v_exponents
    
    plt_aef = v.copy()
    x = 10.0
    
    # Extend vector down to 10^-6
    for _ in range(6):
        plt_aef = np.concatenate((plt_aef, v[1:] / x))
        x = x * 10.0
        
    plt_aef = np.flip(plt_aef) # Low freq to high freq

    # Create the table vector (tbl_aef)
    tbl_denominators = np.array([0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 
                                 500, 1000, 2000, 5000, 10000, 20000, 50000, 
                                 100000, 200000, 500000, 1000000])
    tbl_aef = 1.0 / tbl_denominators

    return plt_aef, tbl_aef

# ==========================================
# 4. Plot Hazards
# ==========================================
def plot_hc(
    data: NDArray,
    percentiles: Sequence[float] | None = None,
    file_name: str | Path = "plot.png",
    ylabel: str = "",
    width: float = 7,
    height: float = 4.5,
    tick_fontsize: float = 13,
    label_fontsize: float = 14,
    legend_fontsize: float = 14,
    legend_location: str = "lower center",
    write_fig: bool = True,
    dpi: int = 300,
    use_aep: bool = False,
    line_styles: Sequence[str] = ("--", "-.", ":", (0, (3, 1, 1, 1))),
):
    """Standalone plotting function with safe handling of percentiles."""

    # -----------------------------
    # Figure setup
    # -----------------------------
    fig, ax = plt.subplots(1, 1, figsize=(width, height))

    # -----------------------------
    # Build percentile labels safely
    # -----------------------------
    labels = []
    if percentiles:
        for it in percentiles:
            if it is None:
                continue
            s = f"{it:.2f}".rstrip("0")
            labels.append(s[:-1] if s.endswith(".") else s)

    # -----------------------------
    # Validate shape only if labels exist
    # -----------------------------
    _, n = data.shape
    if labels:
        expected = n - 2
        if len(labels) != expected:
            raise ValueError(
                f"Expected {expected} percentile labels, got {len(labels)}"
            )

    # -----------------------------
    # Plot mean
    # -----------------------------
    x = data[:, 0]
    ax.semilogx(x, data[:, 1], label="Mean")

    # -----------------------------
    # Plot percentile curves
    # -----------------------------
    for i, (label, style) in enumerate(zip(labels, line_styles), start=2):
        ax.semilogx(x, data[:, i], label=f"{label}%", linestyle=style)

    # -----------------------------
    # Flip x-axis
    # -----------------------------
    x0, x1 = ax.get_xlim()
    ax.set_xlim((x1, x0))

    # -----------------------------
    # Grid
    # -----------------------------
    ax.grid(True, which="major")
    ax.grid(True, which="minor", linestyle="--")

    # -----------------------------
    # Axis labels
    # -----------------------------
    xlabel = (
        r"Annual Exceedance Probability"
        if use_aep
        else r"Annual Exceedance Frequency (yr$^{-1}$)"
    )

    ax.set_xlabel(xlabel, fontsize=label_fontsize)
    ax.set_ylabel(ylabel, fontsize=label_fontsize)

    ax.tick_params(axis="both", labelsize=tick_fontsize)

    # -----------------------------
    # Legend
    # -----------------------------
    ax.legend(
        loc=legend_location,
        fontsize=legend_fontsize,
        ncols=(n + 1) if labels else 1,
    )

    # -----------------------------
    # Save or return
    # -----------------------------
    if write_fig:
        file_name = Path(file_name)
        plt.savefig(file_name, dpi=dpi, bbox_inches="tight")
        plt.close()
    else:
        return plt, ax, fig


