FROM python:3.12-slim

# Clean up apt cache after installing packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    nodejs \
    npm && \
    rm -rf /var/lib/apt/lists/*

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

#TODO: Not needed maybe
RUN pip install fastapi uvicorn

ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

COPY . /app/

CMD ["/root/.local/bin/uv", "run", "app.py"]