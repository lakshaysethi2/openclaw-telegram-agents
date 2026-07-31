# Friend Bot agent-3 image: stock OpenClaw + ffmpeg for voice/media delivery.
FROM ghcr.io/openclaw/openclaw:latest

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

USER node
