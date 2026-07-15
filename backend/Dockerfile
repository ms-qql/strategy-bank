FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g opencode-ai

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt
COPY . .

ENV OPENCODE_BINARY=/usr/local/bin/opencode \
    OPENCODE_CONFIG=/app/opencode.json
EXPOSE 8000
CMD ["python3", "entrypoint.py"]
