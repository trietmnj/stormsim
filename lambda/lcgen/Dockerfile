# Use the official AWS Lambda Python 3.11 base image
FROM public.ecr.aws/lambda/python:3.11

# Set the working directory inside the container
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the necessary project files and directories from the build context (root)
COPY classes/ ./classes/
COPY implementation-scripts/ ./implementation_scripts/
# Copy the lambda handler from its sub-directory to the task root
COPY lambda/lcgen/lambda_function.py .

# Set the PYTHONPATH to include the task root
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}:${PYTHONPATH}"

# Set the command for the Lambda handler
CMD [ "lambda_function.handler" ]
