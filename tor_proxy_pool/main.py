import asyncio
import logging
import sys
import os
from colorama import init, Fore, Style

# Configure parent imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tor_proxy_pool.tor_manager import TorManager
from tor_proxy_pool.proxy_server import ProxyServer
from tor_proxy_pool.config import PROXY_PORT, ROTATION_INTERVAL, NUM_INSTANCES

# Initialize colorama
init(autoreset=True)

# Custom premium logging formatter
class CustomFormatter(logging.Formatter):
    format_str = "%(asctime)s | %(levelname)-7s | %(message)s"
    
    FORMATS = {
        logging.DEBUG: Fore.WHITE + Style.DIM + format_str + Style.RESET_ALL,
        logging.INFO: Fore.CYAN + format_str + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + Style.BRIGHT + format_str + Style.RESET_ALL,
        logging.ERROR: Fore.RED + Style.BRIGHT + format_str + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + format_str + Style.RESET_ALL,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

# Set up beautiful console logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CustomFormatter())
root_logger.addHandler(handler)

logger = logging.getLogger(__name__)

async def auto_rotate_task(tor_manager):
    """Background task to rotate all Tor circuits at regular intervals."""
    while True:
        try:
            await asyncio.sleep(ROTATION_INTERVAL)
            logger.warning("Interval reached! Triggering automatic IP rotations...")
            tor_manager.rotate_all_ips()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in automatic rotation task: {e}")
            await asyncio.sleep(10)

async def main():
    print(Fore.MAGENTA + Style.BRIGHT + r"""
==========================================================
  _____  ____  _____     _____  _____   ______   ____   _ 
 |_   _||    ||  __ \   |  __ \|  __ \ /  __  \ \    / | |
   | |  | || || |__) |  | |__) || |__) || |  | |  \  /  | |
   | |  | || ||  _  /   |  ___/ |  _  / | |  | |   \/   | |
   | |  | || || | \ \   | |     | | \ \ | |__| |  /  \  | |____
   |_|  |____||_|  \_\  |_|     |_|  \_\ \______//____\ |______|
==========================================================
       Portable Rotating Tor Proxy Pool Server for Windows
""")
    print(Fore.GREEN + f"[*] Launching proxy server with {NUM_INSTANCES} backend Tor instances...")
    print(Fore.GREEN + f"[*] Local Entry Point: {Fore.YELLOW}http://127.0.0.1:{PROXY_PORT}")
    print(Fore.GREEN + f"[*] IP Rotation Frequency: every {ROTATION_INTERVAL}s")
    print(Fore.WHITE + Style.DIM + "-" * 58)

    tor_manager = TorManager()
    proxy_server = ProxyServer(tor_manager)

    try:
        # 1. Spawn all backend Tor processes
        tor_manager.start_instances()

        # 2. Start the HTTP SOCKS5 Load-balancer server
        await proxy_server.start()

        # 3. Start background interval IP rotation task
        rotation_task = asyncio.create_task(auto_rotate_task(tor_manager))

        logger.info(Fore.GREEN + Style.BRIGHT + f"--- Rotating Proxy is fully active on port {PROXY_PORT}! Press Ctrl+C to terminate ---")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.warning("\nShutdown signal received. Initiating graceful cleanup...")
    except Exception as e:
        logger.error(f"Critical error occurred in server: {e}")
    finally:
        # Stop proxy server
        await proxy_server.stop()
        # Cancel rotation task
        if 'rotation_task' in locals():
            rotation_task.cancel()
            try:
                await rotation_task
            except asyncio.CancelledError:
                pass
        # Stop background Tor instances
        tor_manager.stop_all_instances()
        logger.info(Fore.GREEN + Style.BRIGHT + "Proxy Pool stopped successfully. All instances cleared. Goodbye!")

if __name__ == "__main__":
    try:
        # Windows ProactorEventLoop is required for async socket management on Win32
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
