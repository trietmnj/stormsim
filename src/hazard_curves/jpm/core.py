from pathlib import Path
from typing import Annotated, Optional

import numpy as np
from numpy.typing import NDArray
from pydantic import Field, NonNegativeFloat, PositiveFloat
from pydantic.dataclasses import dataclass
from scipy.stats import norm

from ..common import CaseInsensitiveEnum


class IntegrationEnum(CaseInsensitiveEnum):
    ATCS = 1
    ITCS = 2


class UncertaintyEnum(CaseInsensitiveEnum):
    ABSOLUTE = 1
    RELATIVE = 2
    COMBINED = 3


class TideEnum(CaseInsensitiveEnum):
    NONE = 1
    COMBINED = 2
    PREPROCESS = 3


PercentileFloat = Annotated[float, Field(ge=0, le=100)]

@dataclass
class Options:
    # Flag values to filter out response data
    flag_value: Optional[list[float]] = None
    # Uncertainty parameters
    ua: Optional[PositiveFloat] = None
    ur: Optional[PositiveFloat] = None
    # Sea level change
    slc: NonNegativeFloat = 0.0
    # Standard deviation for tide statistics 
    tide_std: Optional[NonNegativeFloat] = None
    # Percentile ranges for hazard curve
    percentiles: list[PercentileFloat] = Field(
        default=[2.28, 15.87, 84.13, 97.72], min_length=1, max_length=4
    )
    integration_mode: IntegrationEnum = IntegrationEnum.ATCS
    uncertainty_mode: UncertaintyEnum = UncertaintyEnum.COMBINED
    tide_mode: TideEnum = TideEnum.COMBINED
    skewed: Optional[bool] = None
    # Use AEP instead of return periods for x-axis
    use_aep: bool = False
    # Compute hazard curve in table form
    return_table: bool = False
    output_path: Path | str = Path()
    # Partition uncertainties
    # Note: Changed hard-coded values to 'hidden' options
    _p1_a: PositiveFloat = 0.1
    _p1_r: PositiveFloat = 0.1

    def __post_init__(self):
        """Advance validation of arguments combinations"""
        if isinstance(self.output_path, str):
            self.output_path = Path(self.output_path)

        # Validating tide mode arguments
        match self.tide_mode:
            case TideEnum.NONE:
                if not self.tide_std is None:
                    raise ValueError(
                        f"Can not specifiy tide_std with tide_mode={self.tide_mode.name}"
                    )

                if not self.skewed is None:
                    if self.skewed:
                        raise ValueError(
                            f"Can not specifiy skewed with tide_mode={self.tide_mode.name}"
                        )

                self.tide_std = 0
                self.skewed = False

            case TideEnum.COMBINED:
                if not self.skewed is None:
                    if self.skewed:
                        raise ValueError(
                            f"Can not specifiy skewed with tide_mode={self.tide_mode.name}"
                        )
                self.skewed = False

            case TideEnum.PREPROCESS:
                if not self.skewed:
                    if not self.tide_std is None:
                        raise ValueError(
                            f"Can not specifiy tide_std with tide_mode={self.tide_mode.name}"
                        )
                    self.tide_std = 0

            case _:
                # Safety check
                raise NotImplementedError(
                    f"Unsupported enum value '{self.name}' for IntegrationEnum."
                )

        # Validating uncertainty mode arguments
        match self.uncertainty_mode:
            case UncertaintyEnum.RELATIVE:
                ua_required = False
                ur_required = True

            case UncertaintyEnum.ABSOLUTE:
                ua_required = True
                ur_required = False

            case UncertaintyEnum.COMBINED:
                ua_required = True
                ur_required = True

            case _:
                # Safety check
                raise NotImplementedError(
                    f"Unsupported enum value '{self.name}' for UncertaintyEnum."
                )

        def check(suffix: str, required: bool) -> None:
            """Wrapper for validating uncertainty terms"""
            uname = f"u{suffix}"
            u = getattr(self, uname)
            is_val = not u is None
            if required:
                if not is_val:
                    raise ValueError(
                        f"{uname} must be specified with uncertainty_mode={self.uncertainty_mode.name}"
                    )
            else:
                if is_val:
                    raise ValueError(
                        f"Can not specifiy {uname} with uncertainty_mode={self.uncertainty_mode.name}"
                    )
                u = 0.0
                setattr(self, uname, u)

            if self.integration_mode == IntegrationEnum.ITCS:
                pname = f"_p1_{suffix}"
                p1 = getattr(self, pname)

                check = u**2 - p1**2
                if check > 0:
                    u = np.sqrt(check)
                    setattr(self, uname, u)

        check("a", ua_required)
        check("r", ur_required)

        self.percentiles = sorted(self.percentiles)

    def apply_confidence_limits(self, y: NDArray) -> NDArray:

#        assert isinstance(self.tide_std, float)
#        assert isinstance(self.ua, float)
#        assert isinstance(self.ur, float)

        match self.uncertainty_mode:

            case UncertaintyEnum.ABSOLUTE:
                factor = np.hypot(self.ua, self.tide_std)

            case UncertaintyEnum.RELATIVE:
                a = y[:, None] * self.ur,
                b = self.tide_std
                factor =  y[:,None]*np.hypot(a, b)

            case UncertaintyEnum.COMBINED:
                a = 1/self.ua 
                b =  1 / (y[:, None] * self.ur)
                if self.tide_std == 0:
                    factor = 1/np.hypot(a,b)
                else:
                    c = 1 / self.tide_std
                    factor = 1/np.sqrt(a**2 + b**2 + c**2)


        z = norm.ppf(np.array(self.percentiles) / 100.0)
        yp = y[:, None] + z[None, :] * factor
        return np.column_stack([y, yp])


    def get_random_norm(self, n: int) -> NDArray:
        """Returns to probability distribution for tide preprocessing before integration"""
        #assert self.tide_mode == TideEnum.PREPROCESS

        match self.integration_mode:
            case IntegrationEnum.ATCS:
                return np.random.randn(n)
            case IntegrationEnum.ITCS:
                return _get_gaussian_norm()


#fmt: off
def _get_gaussian_norm() -> NDArray:
    return np.array([
        -3.0004, -2.6927, -2.525, -2.4072, -2.3156, -2.2401, -2.1755, -2.1189,
        -2.0683, -2.0226, -1.9807, -1.942, -1.9061, -1.8725, -1.8408, -1.8109,
        -1.7825, -1.7555, -1.7297, -1.7051, -1.6814, -1.6586, -1.6367, -1.6155,
        -1.595, -1.5752, -1.556, -1.5373, -1.5192, -1.5015, -1.4843, -1.4675,
        -1.4511, -1.4352, -1.4195, -1.4042, -1.3893, -1.3746, -1.3602, -1.3461,
        -1.3323, -1.3187, -1.3054, -1.2922, -1.2793, -1.2666, -1.2542, -1.2419,
        -1.2297, -1.2178, -1.206, -1.1944, -1.183, -1.1717, -1.1606, -1.1496,
        -1.1387, -1.128, -1.1174, -1.1069, -1.0966, -1.0863, -1.0762, -1.0662,
        -1.0563, -1.0465, -1.0367, -1.0271, -1.0176, -1.0082, -0.9988, -0.9896,
        -0.9804, -0.9713, -0.9623, -0.9534, -0.9445, -0.9358, -0.927, -0.9184,
        -0.9098, -0.9013, -0.8929, -0.8845, -0.8762, -0.8679, -0.8598, -0.8516,
        -0.8435, -0.8355, -0.8275, -0.8196, -0.8117, -0.8039, -0.7961, -0.7884,
        -0.7807, -0.7731, -0.7655, -0.758, -0.7505, -0.743, -0.7356, -0.7282,
        -0.7209, -0.7136, -0.7063, -0.6991, -0.6919, -0.6848, -0.6776, -0.6706,
        -0.6635, -0.6565, -0.6495, -0.6426, -0.6356, -0.6288, -0.6219, -0.6151,
        -0.6083, -0.6015, -0.5947, -0.588, -0.5813, -0.5746, -0.568, -0.5614,
        -0.5548, -0.5482, -0.5417, -0.5351, -0.5286, -0.5221, -0.5157, -0.5093,
        -0.5028, -0.4964, -0.4901, -0.4837, -0.4774, -0.4711, -0.4648, -0.4585,
        -0.4523, -0.446, -0.4398, -0.4336, -0.4274, -0.4212, -0.4151, -0.4089,
        -0.4028, -0.3967, -0.3906, -0.3845, -0.3784, -0.3724, -0.3663, -0.3603,
        -0.3543, -0.3483, -0.3423, -0.3363, -0.3304, -0.3244, -0.3185, -0.3125,
        -0.3066, -0.3007, -0.2948, -0.2889, -0.283, -0.2772, -0.2713, -0.2655,
        -0.2596, -0.2538, -0.248, -0.2422, -0.2363, -0.2306, -0.2248, -0.219,
        -0.2132, -0.2074, -0.2017, -0.1959, -0.1902, -0.1844, -0.1787, -0.173,
        -0.1672, -0.1615, -0.1558, -0.1501, -0.1444, -0.1387, -0.133, -0.1273,
        -0.1216, -0.1159, -0.1103, -0.1046, -0.0989, -0.0932, -0.0876, -0.0819,
        -0.0763, -0.0706, -0.0649, -0.0593, -0.0536, -0.048, -0.0423, -0.0367,
        -0.031, -0.0254, -0.0197, -0.0141, -0.0085, -0.0028, 0.0028, 0.0085,
        0.0141, 0.0197, 0.0254, 0.031, 0.0367, 0.0423, 0.048, 0.0536, 0.0593,
        0.0649, 0.0706, 0.0763, 0.0819, 0.0876, 0.0932, 0.0989, 0.1046, 0.1103,
        0.1159, 0.1216, 0.1273, 0.133, 0.1387, 0.1444, 0.1501, 0.1558, 0.1615,
        0.1672, 0.173, 0.1787, 0.1844, 0.1902, 0.1959, 0.2017, 0.2074, 0.2132,
        0.219, 0.2248, 0.2306, 0.2363, 0.2422, 0.248, 0.2538, 0.2596, 0.2655,
        0.2713, 0.2772, 0.283, 0.2889, 0.2948, 0.3007, 0.3066, 0.3125, 0.3185,
        0.3244, 0.3304, 0.3363, 0.3423, 0.3483, 0.3543, 0.3603, 0.3663, 0.3724,
        0.3784, 0.3845, 0.3906, 0.3967, 0.4028, 0.4089, 0.4151, 0.4212, 0.4274,
        0.4336, 0.4398, 0.446, 0.4523, 0.4585, 0.4648, 0.4711, 0.4774, 0.4837,
        0.4901, 0.4964, 0.5028, 0.5093, 0.5157, 0.5221, 0.5286, 0.5351, 0.5417,
        0.5482, 0.5548, 0.5614, 0.568, 0.5746, 0.5813, 0.588, 0.5947, 0.6015,
        0.6083, 0.6151, 0.6219, 0.6288, 0.6356, 0.6426, 0.6495, 0.6565, 0.6635,
        0.6706, 0.6776, 0.6848, 0.6919, 0.6991, 0.7063, 0.7136, 0.7209, 0.7282,
        0.7356, 0.743, 0.7505, 0.758, 0.7655, 0.7731, 0.7807, 0.7884, 0.7961,
        0.8039, 0.8117, 0.8196, 0.8275, 0.8355, 0.8435, 0.8516, 0.8598, 0.8679,
        0.8762, 0.8845, 0.8929, 0.9013, 0.9098, 0.9184, 0.927, 0.9358, 0.9445,
        0.9534, 0.9623, 0.9713, 0.9804, 0.9896, 0.9988, 1.0082, 1.0176, 1.0271,
        1.0367, 1.0465, 1.0563, 1.0662, 1.0762, 1.0863, 1.0966, 1.1069, 1.1174,
        1.128, 1.1387, 1.1496, 1.1606, 1.1717, 1.183, 1.1944, 1.206, 1.2178,
        1.2297, 1.2419, 1.2542, 1.2666, 1.2793, 1.2922, 1.3054, 1.3187, 1.3323,
        1.3461, 1.3602, 1.3746, 1.3893, 1.4042, 1.4195, 1.4352, 1.4511, 1.4675,
        1.4843, 1.5015, 1.5192, 1.5373, 1.556, 1.5752, 1.595, 1.6155, 1.6367,
        1.6586, 1.6814, 1.7051, 1.7297, 1.7555, 1.7825, 1.8109, 1.8408, 1.8725,
        1.9061, 1.942, 1.9807, 2.0226, 2.0683, 2.1189, 2.1755, 2.2401, 2.3156,
        2.4072, 2.525, 2.6927, 3.0004
    ])
#fmt:on
