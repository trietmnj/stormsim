# Use the official AWS Lambda Python 3.11 base image
FROM public.ecr.aws/lambda/python:3.11

# Set the working directory inside the container
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the requirements file
COPY requirements.txt .

# 1. Install GCC and C++ compilers (needed if wheels aren't available for some dependencies)
# 2. Upgrade pip, setuptools, and wheel to ensure the latest wheel compatibility
# 3. Install requirements
# 4. Clean up to keep the image size smaller
RUN yum install -y gcc gcc-c++ && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    yum remove -y gcc gcc-c++ && \
    yum clean all

# Copy the necessary project files and directories from the build context (root)
COPY classes/ ./classes/
COPY implementation-scripts/ ./implementation_scripts/
# Copy the lambda handler from its sub-directory to the task root
COPY lambda/lcgen/lambda_function.py .

# Set the PYTHONPATH to include the task root
# Using a static value to avoid the "UndefinedVar" warning
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"

# Set the command for the Lambda handler
CMD [ "lambda_function.handler" ]
