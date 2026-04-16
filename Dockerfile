# Dockerfile
FROM python:3.12-slim-bookworm

# System deps: Xvfb, PyAutoGUI, Chrome dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    xvfb x11-utils \
    libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    scrot python3-tk python3-dev \
    fonts-liberation libgtk-3-0 libvulkan1 xdg-utils \
    libcurl4 \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome stable (deps already present above)
RUN wget -q -O /tmp/chrome.deb \
    https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y -f /tmp/chrome.deb \
    && rm /tmp/chrome.deb

# Install uv for fast dependency install
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy everything needed for install first
COPY pyproject.toml .
COPY src/ src/

# Non-editable install (editable install not needed in container)
RUN uv pip install --system "."

# Pre-download UC chromedriver (caches at build time)
RUN python -c "from seleniumbase import drivers; import subprocess; subprocess.run(['sbase', 'get', 'chromedriver', '--path=/usr/local/bin'], check=False)" || true

EXPOSE 8765

CMD ["python", "-m", "src.mcp_server.server"]
