import socket

# Hardcoded loopback interface and port
HOST = '127.0.0.1'
PORT = 65432

def generate_pattern():
    """Generates the repeating alphabet pattern: 80 'a', 80 'b' ... 80 'z'"""
    # ascii 97 to 122 represent 'a' through 'z'
    return b''.join(bytes([char]) * 80 for char in range(97, 123))

def start_server():
    # Pre-compute the 2080-byte repeating chunk to avoid CPU overhead during transfer
    pattern_chunk = generate_pattern()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        # Allow immediate port reuse after restart
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.listen()
        
        print(f"Server listening on {HOST}:{PORT}...")
        
        while True:
            conn, addr = server_socket.accept()
            with conn:
                # 1. Read the request byte-by-byte until newline (Protocol: "SIZE:<bytes>\n")
                req_buffer = b""
                while b"\n" not in req_buffer and len(req_buffer) < 64:
                    chunk = conn.recv(1)
                    if not chunk:
                        break
                    req_buffer += chunk
                
                # 2. Parse the requested size
                if not req_buffer.startswith(b"SIZE:"):
                    print("Invalid request format. Dropping connection.")
                    continue
                
                try:
                    size_str = req_buffer.split(b":")[1].strip()
                    requested_bytes = int(size_str)
                    print(f"Received request from {addr} for {requested_bytes} bytes.")
                except ValueError:
                    print("Invalid size value. Dropping connection.")
                    continue
                
                # 3. Stream the exact amount of requested data
                bytes_sent = 0
                while bytes_sent < requested_bytes:
                    remaining = requested_bytes - bytes_sent
                    
                    # Send the full chunk, or truncate it if we are on the final piece
                    to_send = pattern_chunk if remaining >= len(pattern_chunk) else pattern_chunk[:remaining]
                    
                    conn.sendall(to_send)
                    bytes_sent += len(to_send)
                
                print(f"Transfer complete. Sent {bytes_sent} bytes. Waiting for next request...\n")

if __name__ == "__main__":
    start_server()