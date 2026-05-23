FROM python:3.10-slim

# Install system dependencies, including Tor
RUN apt-get update && apt-get install -y \
    tor \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user (Hugging Face Spaces runs as user with UID 1000)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements first to leverage caching
COPY --chown=user tor_proxy_pool/requirements.txt requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application files
COPY --chown=user . .

# Expose Hugging Face's default port (7860)
EXPOSE 7860

# Run the proxy pool
CMD ["python", "-u", "tor_proxy_pool/main.py"]
