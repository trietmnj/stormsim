import os
from pathlib import Path
from typing import Dict, Optional, Any

class StorageContext:
    """
    Unified storage handler for StormSim.
    Resolves Local vs. S3 paths and manages AWS credentials for 
    lcgen, hydrograph_manipulator, and eurotop.
    """
    def __init__(
        self, 
        config: Dict[str, Any], 
        s3_config_override: Optional[Dict] = None,
        is_lambda: bool = False
    ):
        self.config = config
        self.inputs = config.get("inputs", {})
        self.outputs = config.get("outputs", {})
        self.is_lambda = is_lambda
        
        # 1. Determine locality FIRST
        self.use_local = self._determine_locality()

        # 2. S3 configuration
        self.s3_config = self._init_s3_config(s3_config_override)

    def _determine_locality(self) -> bool:
        if self.is_lambda:
            is_sam_local = os.getenv("AWS_SAM_LOCAL", "").lower() == "true"
            env_force_local = os.getenv("LCGEN_USE_LOCAL_INPUTS", "").lower() in {"1", "true", "yes"}
            if is_sam_local and env_force_local:
                return True
            return bool(self.inputs.get("use_local_inputs", False))
        
        return not (self.inputs.get("use_s3", False) or self.config.get("s3_config", {}).get("use_s3", False))

    def _init_s3_config(self, override: Optional[Dict]) -> Dict:
        raw = override or self.config.get("s3_config", {})
        
        # Use S3 if we are in Lambda (and not local) or if explicitly enabled
        use_s3 = not self.use_local if self.is_lambda else (raw.get("use_s3") or self.inputs.get("use_s3", False))
        
        # IMPORTANT: We only take what is explicitly provided in the config.
        # We do NOT manually pull AWS_ACCESS_KEY_ID etc. from the environment.
        # If running in AWS Lambda with an IAM Role, we omit keys entirely so 
        # the SDK (boto3/s3fs) can handle the temporary credentials natively.
        return {
            "use_s3": use_s3,
            "s3_endpoint": raw.get("endpoint"),
            "s3_access_key": raw.get("access_key"),
            "s3_secret_key": raw.get("secret_key"),
        }

    def resolve_path(self, path: str) -> str:
        """Resolves a raw string path to a usable local path or S3 URL."""
        if not path or path.startswith("s3://"):
            return path

        if self.use_local:
            root = os.environ.get("LAMBDA_TASK_ROOT", "").strip()
            if root and self.is_lambda and not os.path.isabs(path):
                return str(Path(root) / path)
            return path

        # S3 construction using input defaults
        bucket = self.inputs.get("s3_bucket", "chart-dev")
        prefix = self.inputs.get("s3_prefix", "").strip("/")
        filename = Path(path).name
        return f"s3://{bucket}/{prefix}/{filename}" if prefix else f"s3://{bucket}/{filename}"

    def get_input_path(self, key: str) -> str:
        """Helper to resolve a specific key from the inputs config."""
        return self.resolve_path(self.inputs.get(key, ""))

    def get_output_path(self) -> str:
        """Resolves the output destination based on config."""
        # Every caller of this path writes parquet (see write_parquet), so the
        # default name said .csv about a file that was never CSV.
        filename = self.outputs.get("filename", "output.parquet")
        if self.outputs.get("storage_type") == "s3":
            bucket = self.outputs["s3_bucket"]
            prefix = self.outputs.get("s3_prefix", "").strip("/")
            return f"s3://{bucket}/{prefix}/{filename}" if prefix else f"s3://{bucket}/{filename}"
        
        out_dir = Path(self.outputs.get("local_directory", "output"))
        out_dir.mkdir(parents=True, exist_ok=True)
        return str(out_dir / filename)

    def get_pandas_storage_options(self) -> Optional[Dict]:
        if not self.s3_config.get("use_s3"):
            return None
        
        opts = {}
        # Only pass credentials if they were explicitly provided in s3_config
        if self.s3_config.get("s3_access_key"):
            opts["key"] = self.s3_config["s3_access_key"]
        if self.s3_config.get("s3_secret_key"):
            opts["secret"] = self.s3_config["s3_secret_key"]
        
        if self.s3_config.get("s3_endpoint"):
            opts["client_kwargs"] = {"endpoint_url": self.s3_config["s3_endpoint"]}
            
        return opts if opts else None
