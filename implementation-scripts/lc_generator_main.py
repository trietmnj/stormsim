import json
import argparse
from pathlib import Path
from typing import Dict
from stormsim.lcgen import run_lc_generator

# -----------------------------
# CONFIG LOADING
# -----------------------------
DEFAULT_CONFIG = Path("data/lcgen/config_local.json")

def load_config(path: Path) -> Dict:
    with open(path, "r") as f:
        return json.load(f)

# -----------------------------
# MAIN DRIVER
# -----------------------------
def main(config_path: Path):
    config = load_config(config_path)
    print(f"Using CLI Entry point with config: {config_path}")

    if config["runtime"].get("profile", False):
        import cProfile
        import pstats
        import io

        pr = cProfile.Profile()
        pr.enable()

        # Call the library function directly
        result = run_lc_generator(config)
        print(result)

        pr.disable()
        s = io.StringIO()
        ps = pstats.Stats(pr, stream=s).sort_stats("cumtime")
        ps.print_stats(40)
        print(s.getvalue())
    else:
        # Call the library function directly
        result = run_lc_generator(config)
        print(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lifecycle Generator CLI Wrapper")
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG),
        help=f"Path to the config JSON"
    )
    args = parser.parse_args()
    main(Path(args.config))
