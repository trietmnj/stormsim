import json
import numpy as np
from scipy.interpolate import interp1d
from stormsim import sea_level_rise as slr

class HydroManipulator:
    def __init__(self, config_path=None):
        """
        Initialize HydroManipulator with optional JSON config (file path or dict).
        """
        self.config = {}

        if isinstance(config_path, dict):
            self.config = config_path
        elif config_path:
            self.load_config(config_path)

    def load_config(self, config_path):
        """
        Load configuration from JSON file.
        """
        with open(config_path, 'r') as f:
            self.config = json.load(f)[0]  # assuming single dict in list

    def correct_bias(self, surge_val, Ba, Br):
        """
        Calculates the surge response based on Ba and Br parameters.

        Args:
            surge_val (float or np.array): The input surge value (x).
            Ba (float): B_a_SWL parameter.
            Br (float): B_r_SWL parameter.

        Returns:
            float or np.array: The calculated result.
        """
        # 1. Calculate the sign term: Ba / |Ba|
        sign_Ba = Ba / np.abs(Ba)

        # 2. Calculate the term inside the square root
        # MATLAB: 1./B_a_SWL.^2 + 1./(B_r_SWL .* x).^2
        term_inside_sqrt = (1 / Ba**2) + (1 / (Br * surge_val)**2)

        # 3. Final Calculation
        # MATLAB: x - (sign_Ba) ./ sqrt(...)
        result = surge_val - (sign_Ba / np.sqrt(term_inside_sqrt))

        return result

    def add_slr(self, data_in, adjustment):
        """
        Apply sea level rise adjustment if enabled in config.
        """
        data_out = data_in + adjustment
        
        return data_out
    

    def get_slr_projections(self, slr_projection, slr_scenario, alpha, start_year, end_year):
        # Get Beta Values For Requested Projection
        beta_table = slr.beta_scenarios.print_beta_table(slr_projection)
        # Get Beta Value Col
        beta = beta_table.iloc[:, 1].to_numpy()

        # Generate the DataFrame with all porjection curves
        slr_scenarios_df = slr.sea_level_rise.generate_slr_curves(alpha, beta, start_year, end_year)
        scenario_list = beta_table.iloc[:, -1].to_list()

        # Keep Requested Scenario
        for ii, name in enumerate(scenario_list):
            print(ii)
            if name.lower() == slr_scenario:
                slr_scenarios_df = slr_scenarios_df[['year',f"scenario{ii+1}"]]
                slr_scenarios_df.columns = ['year', slr_scenario] 

        return beta_table, slr_scenarios_df

    def add_tides(self, data_in, time_in, tide_signal, tide_time):
        # Interp Tidal Signal To Input Signal
        interp_tide = self.interp_hydrograph(tide_signal, tide_time, time_in)
        # Add Adjustment
        data_with_tides = data_in + interp_tide

        return data_with_tides

    def interp_hydrograph(self, y, t, tq):
        """
        Linear interpolation of signal values at query times.

        Parameters
        ----------
        y : array-like
            Values of original signal
        t : array-like of datetime
            Time values of original signal
        tq : array-like of datetime
            Query time points

        Returns
        -------
        yq : np.ndarray
            Interpolated values at tq
        """
        # Convert datetime arrays to numeric (seconds since t[0])
        t0 = t[0]
        t_sec  = np.array([(ti - t0).total_seconds() for ti in t])
        tq_sec = np.array([(tqi - t0).total_seconds() for tqi in tq])

        # Build linear interpolator
        f = interp1d(t_sec, y, kind="linear", fill_value="extrapolate")

        # Evaluate at query points
        yq = f(tq_sec)
        return yq

    def wavenum(self, T, depth, grav):
        """
        Solves linear wave theory dispersion relation for wave number k = 2pi/L.

        Args:
            T (np.array): Wave period (s)
            depth (float or np.array): Water depth (m). Can be scalar or array matching T.
            grav (float): Acceleration of gravity (m/s^2)
        """
        # Ensure T is an array
        T = np.asarray(T, dtype=float)

        # Logic to turn scalar depth into array matching T
        depth = np.asarray(depth, dtype=float)
        if depth.ndim == 0:
            depth = np.full_like(T, depth)

        TOL = 1.0e-5
        fq = 1.0 / T

        # Initial guess
        WHSQ = (depth / grav) * (2 * np.pi * fq)**2
        X1 = np.where(WHSQ > 1.0, WHSQ, np.sqrt(WHSQ))

        # Initialize correction array
        CORR = np.full_like(X1, 1.0)

        # Optimization: Pre-check limits
        deep_mask = np.tanh(X1) > (1.0 - TOL)
        shallow_mask = np.abs(X1 - np.tanh(X1)) < TOL
        CORR[deep_mask | shallow_mask] = 0.0

        iter_count = 0
        max_iter = 100
        error_flag = 1

        # Newton-Raphson Loop
        while np.any(np.abs(CORR) > TOL) and iter_count < max_iter:
            mask = np.abs(CORR) > TOL

            X_active = X1[mask]
            W_active = WHSQ[mask]

            tanh_X = np.tanh(X_active)
            cosh_X = np.cosh(X_active)

            numer = X_active * tanh_X - W_active
            denom = tanh_X + X_active / (cosh_X**2)

            # Slope check
            valid_slope = np.abs(denom) >= TOL
            if not np.all(valid_slope):
                error_flag = 0

            delta = np.zeros_like(X_active)
            delta[valid_slope] = numer[valid_slope] / denom[valid_slope]

            X1[mask] -= delta
            CORR[mask] = delta
            iter_count += 1

        km = X1 / depth

        # Empirical Estimate
        arg = (2 * np.pi / T) * np.sqrt(depth / grav)
        A = (grav * T**2) / (2 * np.pi)
        wavelen = A * (1 - np.exp(-(arg**2.5)))**0.4
        kmest = (2 * np.pi) / wavelen

        return km, kmest, error_flag

    def add_depth_limitation(self, Hm0, Tp, h, g):
        """
        Limits wave height based on depth using empirical breaker index.

        Args:
            Hm0 (np.array): Significant wave height
            Tp (np.array): Peak wave period
            h (float or np.array): Water depth (scalar or matching array)
            g (float): Gravity constant
        """
        # 1. Handle Scalar Depth: Repeat input value if scalar
        # We rely on Tp to determine the target shape
        h = np.asarray(h, dtype=float)
        if h.ndim == 0:
            h = np.full_like(Tp, h)

        # 2. Compute Wave Number
        # Now h is guaranteed to be an array matching Tp
        km, _, _ = self.wavenum(Tp, h, g)
        
        # 3. Compute Depth Limited Waves
        # K_b is set to 1.0 as per your MATLAB code
        K_b = 1.0
        wavelength = (2 * np.pi) / km

        # Formula: K_b * 0.1 * L * tanh(kh)
        depth_limited_waves = K_b * 0.1 * wavelength * np.tanh(km * h)

        # 4. Handle Negative/Invalid Depth Artifacts
        # If the limit comes out negative (due to negative depth input), revert to original Hm0
        invalid_mask = depth_limited_waves <= 0
        depth_limited_waves[invalid_mask] = Hm0[invalid_mask]

        # 5. Apply the Limit
        # Create copy to avoid modifying input in-place
        out_Hm0 = np.copy(Hm0)
        limit_mask = out_Hm0 > depth_limited_waves
        out_Hm0[limit_mask] = depth_limited_waves[limit_mask]

        return out_Hm0, depth_limited_waves
