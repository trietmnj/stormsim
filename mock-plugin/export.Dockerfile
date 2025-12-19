# stormsim-mock-plugin/export.Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1

WORKDIR /app

COPY mock-plugin/seed/damage-functions.json /seed/damage-functions.json
COPY mock-plugin/ /app
COPY mock-plugin/cc-py-sdk/src/cc/ /app/cc/

# Install python dependencies
COPY mock-plugin/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
pip install -r /tmp/requirements.txt

CMD ["python", "app/main.py"]
