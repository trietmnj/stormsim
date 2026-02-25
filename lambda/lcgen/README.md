# Deploying Lifecycle Generator (LCG) to AWS Lambda

This document explains how to package and deploy the Lifecycle Generator to AWS Lambda.

## Repository Organization

- `lambda/lcgen/`: Contains the Lambda-specific files:
  - `lambda_function.py`: The entry point for AWS Lambda.
  - `Dockerfile`: Container definition based on Python 3.12 (AL2023).
  - `requirements.txt`: Lambda-specific dependency pins (e.g., `numpy < 2.0.0`).
  - `README.md`: Deployment instructions.
- `classes/lcgen/`: Contains the core logic for the Lifecycle Generator.
- `implementation-scripts/`: Contains the CLI entry point (`lc_generator_main.py`).

## Deployment Steps

### 1. Build the Docker Image

The build uses the **official AWS Lambda Python 3.12** base image (`public.ecr.aws/lambda/python:3.12`), which is based on **Amazon Linux 2023**. This environment provides **GCC 11.3**, meeting the build requirements for modern scientific Python packages (e.g., `numpy`, `h5py`).

Run the build from the project root directory, pointing to the Dockerfile in `lambda/lcgen/`:

```bash
docker build -t stormsim-lcg-lambda -f lambda/lcgen/Dockerfile .
```

### 2. Push to Amazon ECR

1. Create a repository in Amazon ECR.
2. Tag and push the image:

```bash
aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin your-account-id.dkr.ecr.your-region.amazonaws.com
docker tag stormsim-lcg-lambda:latest your-account-id.dkr.ecr.your-region.amazonaws.com/stormsim-lcg-lambda:latest
docker push your-account-id.dkr.ecr.your-region.amazonaws.com/stormsim-lcg-lambda:latest
```

### 3. Create/Update Lambda Function

1. Create a new Lambda function and select **Container image**.
2. Provide the ECR image URI.
3. Set the **Timeout** to a value appropriate for your simulations (up to 15 minutes).
4. Set the **Memory** (e.g., 2048 MB or more depending on data size).
5. Ensure the Lambda execution role has permissions to read/write to the required S3 buckets.

### 4. Triggering the Simulation

Invoke the Lambda function with a JSON payload that matches the configuration format:

```json
{
  "simulation_params": {
    "initialize_year": 2033,
    "lifecycle_duration": 10,
    "num_lcs": 10,
    "lam_target": 1.7,
    "min_arrival_trop_days": 7.0
  },
  "inputs": {
    "use_duckdb": true,
    "use_s3": true,
    "rel_prob_file": "s3://your-bucket/data/Relative_probability_bins_Atlantic 4.csv",
    "storm_id_prob_file": "s3://your-bucket/data/CHS-NA_Master_Track_Table.csv"
  },
  "outputs": {
    "storage_type": "s3",
    "filename": "EventDate_LC.csv",
    "s3_bucket": "your-bucket",
    "s3_prefix": "lcgen/outputs"
  },
  "runtime": {
    "validate_lambda": true
  }
}
```

## Local Testing with MinIO (Docker Compose)

The easiest way to test S3 integration locally is using Docker Compose, which orchestrates the Lambda container, a MinIO instance, and an automatic data upload step.

### 1. Start the services
From the project root, run:
```bash
docker-compose -f lambda/docker-compose.yml up --build
```
This will:
- Start **MinIO** on `http://localhost:9000`.
- Run a setup container that creates the `stormsim` bucket and uploads your local `data/` folder.
- Start the **Lambda** function on `http://localhost:8081` (mapping to container port 8080).

### 2. Invoke with S3 Payload
In a new terminal, use the `event_s3.json` payload which points to the MinIO container:
```bash
curl -XPOST "http://localhost:8081/2015-03-31/functions/function/invocations" -d @lambda/lcgen/event_s3.json
```

*Note: In the payload, the `s3_endpoint` is `http://minio:9000` because the Lambda container communicates with MinIO over the internal Docker network.*

### Iteration Workflow
1. **Modify Code**: Change logic in `classes/lcgen/` or `lambda/lcgen/lambda_function.py`.
2. **Rebuild**: `docker build -t stormsim-lcg-lambda -f lambda/lcgen/Dockerfile .`
3. **Run**: `docker run -p 8081:8080 stormsim-lcg-lambda`
4. **Invoke**: `curl -XPOST "http://localhost:8081/2015-03-31/functions/function/invocations" -d @event.json`
