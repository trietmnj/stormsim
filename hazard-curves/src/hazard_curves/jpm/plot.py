from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from numpy.typing import NDArray
from pydantic import PositiveFloat, PositiveInt
from pydantic.dataclasses import dataclass
from scipy.stats import norm

from .core import Options


@dataclass
class PlotOptions:

    file_name: str | Path
    ylabel: str
    width: PositiveFloat = 7
    height: PositiveFloat = 4.5
    tick_fontsize: PositiveFloat = 13
    label_fontsize: PositiveFloat = 14
    legend_fontsize: PositiveFloat = 14
    legend_location: str = "lower center"
    dpi: PositiveInt = 300

    _LINE_STYLES_ = ["--", "-.", ":", (0, (3, 1, 1, 1, 1, 1))]

    def plot(self, data: NDArray, opts: Options) -> None:

        figsize = (self.width, self.height)
        fig, ax = plt.subplots(1, 1, figsize=figsize)

        labels = [f"{it:.2f}".rstrip("0") for it in opts.percentiles]
        labels = [it[:-1] if it[-1] == "." else it for it in labels]

        _, n = data.shape
        assert len(labels) == n - 2

        x = data[:, 0]
        ax.semilogx(x, data[:, 1], label="Mean")

        for i, (label, style) in enumerate(zip(labels, self._LINE_STYLES_), start=2):
            ax.semilogx(x, data[:, i], label=f"{label}%", linestyle=style)

        x0, x1 = ax.get_xlim()
        ax.set_xlim((x1, x0))

        ax.grid(True, which="major")
        ax.grid(True, which="minor", linestyle="--")

        if opts.use_aep:
            xlabel = r"Annual Exceedance Probability"
        else:
            xlabel = r"Annual Exceedance Frequency (yr$^{-1}$)"

        plt.xlabel(xlabel, fontsize=self.label_fontsize)
        plt.ylabel(self.ylabel, fontsize=self.label_fontsize)

        plt.xticks(fontsize=self.tick_fontsize)
        plt.yticks(fontsize=self.tick_fontsize)

        plt.legend(
            loc=self.legend_location, fontsize=self.legend_fontsize, ncols=(n + 1)
        )

        fpath = opts.output_path / self.file_name
        plt.savefig(fpath, dpi=self.dpi, bbox_inches="tight")
        plt.close()
