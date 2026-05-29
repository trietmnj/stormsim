import argparse
from stormsim.eurotop import run_aggregate_q


def main():
    parser = argparse.ArgumentParser(description="Aggregate overtopping rates across transects.")
    parser.add_argument(
        "transect_sim_path",
        type=str,
        help="Path to the directory containing transect subfolders.",
    )
    args = parser.parse_args()
    run_aggregate_q({"inputs": {"transect_sim_path": args.transect_sim_path}})


if __name__ == "__main__":
    main()
