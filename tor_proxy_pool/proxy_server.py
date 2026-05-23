import asyncio
import logging
from urllib.parse import urlparse
from tor_proxy_pool.config import PROXY_PORT

logger = logging.getLogger(__name__)

class ProxyServer:
    def __init__(self, tor_manager):
        self.tor_manager = tor_manager
        self.server = None
        self.rr_index = 0  # Round-robin index

    def get_next_tor_socks_port(self):
        """Round-robin selection of the next active Tor SOCKS5 port."""
        processes = self.tor_manager.processes
        if not processes:
            raise Exception("No active Tor instances available in the pool!")
        
        socks_port = processes[self.rr_index]["socks_port"]
        self.rr_index = (self.rr_index + 1) % len(processes)
        return socks_port

    async def socks5_handshake(self, reader, writer, dest_host, dest_port):
        """Performs async SOCKS5 handshake with local Tor instance."""
        # 1. Send client greeting (SOCKS5, 1 auth method: NO AUTH)
        writer.write(b"\x05\x01\x00")
        await writer.drain()

        # 2. Read server response (Version, selected auth method)
        resp = await reader.readexactly(2)
        if resp[0] != 5 or resp[1] != 0:
            raise Exception(f"SOCKS5 server rejected NO AUTH method: {resp}")

        # 3. Send CONNECT request (Version 5, Command 1, Reserved 0, Addr Type 3: DOMAINNAME)
        host_bytes = dest_host.encode('utf-8')
        payload = bytearray([5, 1, 0, 3, len(host_bytes)])
        payload.extend(host_bytes)
        payload.extend(dest_port.to_bytes(2, 'big'))
        
        writer.write(payload)
        await writer.drain()

        # 4. Read SOCKS5 server response header
        resp_header = await reader.readexactly(4)
        if resp_header[0] != 5 or resp_header[1] != 0:
            raise Exception(f"SOCKS5 connection failed. Status code: {resp_header[1]}")

        # Read the rest of the response to clear buffer depending on bound address type
        addr_type = resp_header[3]
        if addr_type == 1:  # IPv4
            await reader.readexactly(6)
        elif addr_type == 3:  # Domain Name
            len_byte = await reader.readexactly(1)
            await reader.readexactly(len_byte[0] + 2)
        elif addr_type == 4:  # IPv6
            await reader.readexactly(18)
        else:
            raise Exception(f"Unsupported SOCKS5 address type: {addr_type}")

    async def pipe(self, reader, writer):
        """Asynchronously pipes data from reader to writer until EOF."""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def handle_client(self, client_reader, client_writer):
        """Handles incoming HTTP or HTTPS CONNECT requests from clients."""
        try:
            # Read first chunk of headers to inspect the request
            header_chunk = await client_reader.read(4096)
            if not header_chunk:
                return

            first_line = header_chunk.split(b'\r\n')[0].decode('utf-8', errors='ignore')
            parts = first_line.split()
            if len(parts) < 3:
                return

            method, url_path, _ = parts
            
            # Select which Tor SOCKS5 instance to route through
            socks_port = self.get_next_tor_socks_port()

            if method.upper() == 'CONNECT':
                # HTTPS CONNECT request: host:port
                host_port = url_path
                if ':' in host_port:
                    dest_host, dest_port_str = host_port.split(':', 1)
                    dest_port = int(dest_port_str)
                else:
                    dest_host = host_port
                    dest_port = 443

                logger.debug(f"Routing HTTPS CONNECT through SocksPort {socks_port} to {dest_host}:{dest_port}")

                # Establish TCP connection to local Tor instance
                socks_reader, socks_writer = await asyncio.open_connection("127.0.0.1", socks_port)
                
                try:
                    # SOCKS5 Handshake over Tor to destination
                    await self.socks5_handshake(socks_reader, socks_writer, dest_host, dest_port)
                    
                    # Connection established, write success back to client
                    client_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                    await client_writer.drain()

                    # Pipe bidirectional traffic between client and Tor SOCKS5
                    await asyncio.gather(
                        self.pipe(client_reader, socks_writer),
                        self.pipe(socks_reader, client_writer)
                    )
                except Exception as he:
                    logger.error(f"SOCKS5 handshake/tunnel failed for {dest_host}:{dest_port}: {he}")
                    client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                    await client_writer.drain()
                    client_writer.close()

            else:
                # Standard HTTP request (GET, POST, etc.)
                parsed = urlparse(url_path)
                dest_host = parsed.hostname or parsed.netloc
                dest_port = parsed.port or (80 if parsed.scheme == 'http' else 443)
                
                # Reconstruct relative request path if necessary
                path = parsed.path
                if parsed.query:
                    path += '?' + parsed.query
                if not path:
                    path = '/'

                # Rebuild HTTP request headers for target server
                reconstructed_first_line = f"{method} {path} HTTP/1.1\r\n"
                headers_part = header_chunk.split(b'\r\n', 1)[1]
                rebuilt_request = reconstructed_first_line.encode('utf-8') + headers_part

                logger.debug(f"Routing HTTP {method} through SocksPort {socks_port} to {dest_host}:{dest_port}")

                socks_reader, socks_writer = await asyncio.open_connection("127.0.0.1", socks_port)
                
                try:
                    await self.socks5_handshake(socks_reader, socks_writer, dest_host, dest_port)
                    
                    # Send our reconstructed request through the SOCKS5 tunnel
                    socks_writer.write(rebuilt_request)
                    await socks_writer.drain()

                    # Pipe remaining bidirectional traffic
                    await asyncio.gather(
                        self.pipe(client_reader, socks_writer),
                        self.pipe(socks_reader, client_writer)
                    )
                except Exception as he:
                    logger.error(f"SOCKS5 HTTP request failed for {dest_host}:{dest_port}: {he}")
                    client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                    await client_writer.drain()
                    client_writer.close()

        except Exception as ce:
            logger.error(f"Error handling proxy client connection: {ce}")
            try:
                client_writer.close()
            except Exception:
                pass

    async def start(self):
        """Starts the proxy server listening for connections."""
        self.server = await asyncio.start_server(
            self.handle_client, "127.0.0.1", PROXY_PORT
        )
        logger.info(f"Asynchronous HTTP Tunneling Proxy is live and listening on 127.0.0.1:{PROXY_PORT}")

    async def stop(self):
        """Stops the proxy server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Proxy server stopped.")
