import os

# Configuration settings for Tor Proxy Pool

# Number of concurrent Tor instances
NUM_INSTANCES = 5

# Starting ports
START_SOCKS_PORT = 9050
START_CONTROL_PORT = 9150

# Main HTTP proxy port (dynamically binds to PORT env var for Hugging Face support)
PROXY_PORT = int(os.getenv("PORT", 8080))

# Auto-rotation interval (seconds) for each instance's IP circuit
ROTATION_INTERVAL = 300  # 5 minutes

# Geo-targeting of Tor exit nodes (e.g. "{us}" for USA, "{de}" for Germany, or None for random/any)
# You can specify multiple countries separated by commas: "{us},{ca},{gb}"
EXIT_COUNTRIES = None

# Tor Windows Expert Bundle URL (stable 14.0.6 archived release to prevent future 404s)
TOR_DOWNLOAD_URL = "https://archive.torproject.org/tor-package-archive/torbrowser/14.0.6/tor-expert-bundle-windows-x86_64-14.0.6.tar.gz"

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOR_DIR = os.path.join(BASE_DIR, "tor_bundle")
DATA_DIR = os.path.join(BASE_DIR, "tor_data")

# Create data directories if they don't exist
os.makedirs(TOR_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
