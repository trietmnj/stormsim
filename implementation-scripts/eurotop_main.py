import json
import argparse
from pathlib import Path
from stormsim.eurotop import run_eurotop

def load_config(path: Path):
    with open(path, 'r') as f:
        return json.load(f)[0] # Current eurotop config is a list of 1 dict

def main():
    parser = argparse.ArgumentParser(description="Eurotop CLI Wrapper")
    parser.add_argument("--config", type=str, default="config-files/eurotop_run_config.json", help="Path to the config JSON")
    args = parser.parse_args()
    
    config_path = Path(args.config)
    config = load_config(config_path)
    print(f"Using CLI Entry point with config: {config_path}")
    
    result = run_eurotop(config)
    print(result)

if __name__ == "__main__":
    main()
