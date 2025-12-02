import pandas as pd


def compute_storm_counts(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    Given a full concatenated lifecycle dataframe,
    return a table of storm counts per (lifecycle, year).
    """
    counts = (
        df_all.groupby(["lifecycle", "year"]).size().rename("n_storms").reset_index()
    )
    return counts


def verify_lambda(counts: pd.DataFrame, lambda_target: float) -> None:
    """
    Print summary stats showing how well the output storm count distribution
    matches the target lambda.
    """
    mean_emp = counts["n_storms"].mean()
    var_emp = counts["n_storms"].var(ddof=0)

    print("\n--- Storm Count Verification ---")
    print(f"Target lambda:       {lambda_target:.4f}")
    print(f"Empirical mean:      {mean_emp:.4f}")
    print(f"Empirical variance:  {var_emp:.4f}")

    # show empirical distribution of N
    value_counts = counts["n_storms"].value_counts().sort_index()
    emp_prob = value_counts / value_counts.sum()

    print("\nk | empirical P(N=k)")
    for k, p in emp_prob.items():
        print(f"{k:2d} | {p:.4f}")
