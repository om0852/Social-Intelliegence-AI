import os
import sys
import shutil
import tarfile
import urllib.request
import subprocess
import socket
import time
import logging
from tor_proxy_pool.config import (
    NUM_INSTANCES, START_SOCKS_PORT, START_CONTROL_PORT,
    TOR_DOWNLOAD_URL, TOR_DIR, DATA_DIR, EXIT_COUNTRIES
)

logger = logging.getLogger(__name__)

class TorManager:
    def __init__(self):
        self.processes = []
        self.tor_exe_path = None

    def ensure_tor_installed(self):
        """Ensures that the Tor Expert Bundle is downloaded and extracted."""
        # Find if tor.exe already exists
        self.tor_exe_path = self._find_tor_exe()
        if self.tor_exe_path:
            logger.info(f"Tor binary already found at: {self.tor_exe_path}")
            return

        # If not found, download the archive
        archive_name = "tor-expert-bundle.tar.gz"
        archive_path = os.path.join(os.path.dirname(TOR_DIR), archive_name)

        if not os.path.exists(archive_path):
            logger.info(f"Downloading Tor Windows Expert Bundle from {TOR_DOWNLOAD_URL}...")
            try:
                # Custom User-Agent to bypass dist.torproject.org block if any
                req = urllib.request.Request(
                    TOR_DOWNLOAD_URL,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                with urllib.request.urlopen(req) as response, open(archive_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                logger.info("Download completed successfully.")
            except Exception as e:
                logger.error(f"Failed to download Tor Expert Bundle: {e}")
                raise Exception(f"Failed to download Tor Expert Bundle: {e}")

        # Extract tar.gz
        logger.info(f"Extracting {archive_name} to {TOR_DIR}...")
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=TOR_DIR)
            logger.info("Extraction completed successfully.")
        except Exception as e:
            logger.error(f"Failed to extract Tor bundle: {e}")
            raise Exception(f"Failed to extract Tor bundle: {e}")

        # Clean up archive
        try:
            os.remove(archive_path)
        except OSError:
            pass

        self.tor_exe_path = self._find_tor_exe()
        if not self.tor_exe_path:
            raise Exception("Could not find tor.exe in the extracted directory structure!")
        logger.info(f"Tor binary is ready at: {self.tor_exe_path}")

    def _find_tor_exe(self):
        """Finds tor binary either globally or in local tor_bundle."""
        import shutil
        # Check if tor is globally installed (Linux / Docker / macOS)
        global_tor = shutil.which("tor")
        if global_tor:
            return global_tor

        # Windows Expert Bundle fallback
        for root, _, files in os.walk(TOR_DIR):
            for file in files:
                if file.lower() == "tor.exe":
                    return os.path.join(root, file)
        return None

    def start_instances(self):
        """Starts specified number of Tor instances with custom torrc configurations."""
        self.ensure_tor_installed()
        
        logger.info(f"Spawning {NUM_INSTANCES} Tor instances...")
        for i in range(NUM_INSTANCES):
            socks_port = START_SOCKS_PORT + (i * 2)
            control_port = START_CONTROL_PORT + i
            instance_data_dir = os.path.join(DATA_DIR, f"instance_{i}")
            os.makedirs(instance_data_dir, exist_ok=True)

            # Generate temporary torrc content
            torrc_path = os.path.join(instance_data_dir, "torrc")
            
            # Escape backslashes for torrc and wrap in double quotes to handle spaces in Windows paths correctly
            safe_data_dir = instance_data_dir.replace('\\', '\\\\')
            
            torrc_content = (
                f'SocksPort 127.0.0.1:{socks_port}\n'
                f'ControlPort 127.0.0.1:{control_port}\n'
                f'DataDirectory "{safe_data_dir}"\n'
            )
            if EXIT_COUNTRIES:
                torrc_content += f'ExitNodes {EXIT_COUNTRIES}\nStrictNodes 1\n'
            with open(torrc_path, "w") as f:
                f.write(torrc_content)

            # Start process in background
            logger.info(f"Starting Tor Instance {i+1}/{NUM_INSTANCES} | SocksPort: {socks_port} | ControlPort: {control_port}")
            
            # Use CREATE_NO_WINDOW flag on Windows to prevent console windows from popping up
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            p = subprocess.Popen(
                [self.tor_exe_path, "-f", torrc_path],
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes.append({
                "index": i,
                "process": p,
                "socks_port": socks_port,
                "control_port": control_port,
                "data_dir": instance_data_dir
            })

        # Wait for all Tor processes to bootstrap SOCKS ports
        self._wait_for_bootstrap()

    def _wait_for_bootstrap(self):
        """Wait until all SOCKS ports are open and listening."""
        logger.info("Waiting for all Tor instances to bootstrap (this can take 10-30 seconds)...")
        start_time = time.time()
        timeout = 60  # seconds

        while time.time() - start_time < timeout:
            all_ready = True
            for proc in self.processes:
                # Check if port is open
                socks_port = proc["socks_port"]
                if not self._is_port_open(socks_port):
                    all_ready = False
                    break
            
            if all_ready:
                logger.info("All Tor instances successfully bootstrapped and ready!")
                return
            time.sleep(1)

        logger.warning("Timeout reached before all Tor instances fully bootstrapped. Some might still be initializing.")

    def _is_port_open(self, port):
        """Checks if a local TCP port is open."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except (socket.timeout, ConnectionRefusedError):
                return False

    def rotate_ip(self, index):
        """Sends the NEWNYM signal to a specific Tor instance via its ControlPort."""
        proc = self.processes[index]
        control_port = proc["control_port"]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect(("127.0.0.1", control_port))
                
                # Receive banner
                s.recv(1024)
                
                # Authenticate (no password configured in our torrc)
                s.sendall(b"AUTHENTICATE \"\"\r\n")
                resp = s.recv(1024).decode('utf-8')
                if "250" not in resp:
                    raise Exception(f"Authentication failed: {resp}")

                # Send signal NEWNYM to rotate circuit
                s.sendall(b"SIGNAL NEWNYM\r\n")
                resp = s.recv(1024).decode('utf-8')
                if "250" not in resp:
                    raise Exception(f"Failed to send NEWNYM: {resp}")
                
                logger.info(f"Successfully rotated IP circuit for Tor Instance {index+1} (SocksPort: {proc['socks_port']})")
                return True
        except Exception as e:
            logger.error(f"Failed to rotate IP for Tor Instance {index+1} (ControlPort: {control_port}): {e}")
            return False

    def rotate_all_ips(self):
        """Rotates IP circuits for all active Tor instances."""
        logger.info("Rotating IP circuits for all Tor instances...")
        for i in range(len(self.processes)):
            self.rotate_ip(i)

    def stop_all_instances(self):
        """Gracefully terminates all background Tor processes."""
        logger.info("Stopping all Tor instances...")
        for proc in self.processes:
            p = proc["process"]
            try:
                p.terminate()
                p.wait(timeout=2.0)
                logger.info(f"Tor Instance {proc['index']+1} terminated.")
            except Exception:
                try:
                    p.kill()
                    logger.info(f"Tor Instance {proc['index']+1} force killed.")
                except Exception:
                    pass
        self.processes = []
