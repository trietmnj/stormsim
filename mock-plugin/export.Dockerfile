# stormsim-mock-plugin/export.Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1

WORKDIR /app

COPY cc-demo/seed/stormsim-mock-plugin/damage-functions.json /seed/damage-functions.json
COPY cc-demo/stormsim-mock-plugin/ /app
COPY cc-py-sdk/src/cc/ /app/cc/

# Install python dependencies
COPY cc-demo/stormsim-mock-plugin/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
pip install -r /tmp/requirements.txt

CMD ["python", "app/main.py"]
