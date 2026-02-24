# Deploying Lifecycle Generator (LCG) to AWS Lambda

This document explains how to package and deploy the Lifecycle Generator to AWS Lambda.

## Repository Organization

- `lambda/lcgen/`: Contains the Lambda-specific files (`lambda_function.py`, `Dockerfile`, `README.md`).
- `classes/lcgen/`: Contains the core logic for the Lifecycle Generator.
- `implementation-scripts/`: Contains the CLI entry point (`lc_generator_main.py`).

## Deployment Steps

### 1. Build the Docker Image

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

## Local Testing with Docker

You can test the Lambda function locally using the [AWS Lambda Runtime Interface Emulator](https://docs.aws.amazon.com/lambda/latest/dg/images-test.html).

### 1. Start the Container
Run the container and map port `8080` (the Lambda endpoint) to your local port `9000`:

```bash
docker run -p 9000:8080 stormsim-lcg-lambda
```

### 2. Prepare a Test Payload (`event.json`)
```json
{
  "simulation_params": {
    "initialize_year": 2025,
    "lifecycle_duration": 5,
    "num_lcs": 2,
    "lam_target": 1.5,
    "min_arrival_trop_days": 7.0
  },
  "inputs": {
    "use_duckdb": true,
    "use_s3": false,
    "rel_prob_file": "data/lcgen/Relative_probability_bins_Atlantic 4.csv",
    "storm_id_prob_file": "data/chs-files/regional-files/CHS-NA_Master_Track_Table.csv"
  },
  "outputs": {
    "storage_type": "local",
    "local_directory": "/tmp/outputs",
    "filename": "local_test_results.csv"
  },
  "runtime": {
    "validate_lambda": true
  }
}
```

### 3. Invoke the Function
In a new terminal, send the payload:

```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d @event.json
```

### Iteration Workflow
1. **Modify Code**: Change logic in `classes/lcgen/` or `lambda/lcgen/lambda_function.py`.
2. **Rebuild**: `docker build -t stormsim-lcg-lambda -f lambda/lcgen/Dockerfile .`
3. **Run**: `docker run -p 9000:8080 stormsim-lcg-lambda`
4. **Invoke**: `curl -XPOST ... -d @event.json`
