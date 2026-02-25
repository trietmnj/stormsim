# Stage 1: Build Stage
FROM public.ecr.aws/lambda/python:3.12 AS builder

# 1. Install build tools (GCC, C++)
RUN dnf install -y gcc gcc-c++

# 2. Set up build directory
WORKDIR /build
COPY lambda/lcgen/requirements.txt .

# 3. Upgrade pip and install dependencies to a target folder
# We install directly to a folder that we will copy to the final image
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt -t ${LAMBDA_TASK_ROOT}

# Stage 2: Final Runtime Stage
FROM public.ecr.aws/lambda/python:3.12

# Set the working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# 1. Copy the installed dependencies from the builder stage
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# 2. Copy project files
COPY classes/ ./classes/
COPY implementation-scripts/ ./implementation_scripts/
COPY lambda/lcgen/lambda_function.py .

# 3. Environment configuration
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

# 4. Lambda handler
CMD [ "lambda_function.handler" ]
