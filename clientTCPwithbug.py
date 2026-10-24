import socket
import argparse
import time

# Hardcoded loopback interface and port
HOST = '127.0.0.1'
PORT = 65432

def start_client(file_size):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        
        client_socket.connect(('',PORT))
        # Format the request according to the protocol
        request = f"SIZE:{file_size}\n".encode('ascii')
        
        print(f"Requesting {file_size} bytes from server...")
        
        # Start timing immediately before sending the request
        start_time = time.perf_counter()
        client_socket.sendall(request)
        
        bytes_received = 0
        first_320_bytes = b""
        
        # Receive the data stream
        while bytes_received < file_size:
            # Receive chunks (up to 4096 bytes or whatever is remaining)
            chunk = client_socket.recv(min(4096, file_size - bytes_received))
            if not chunk:
                break
            
            # Capture the first 320 bytes for display
            if len(first_320_bytes) < 320:
                needed = 320 - len(first_320_bytes)
                first_320_bytes += chunk[:needed]
                
            # "Drop" the file by simply adding to the counter and not writing to disk
            bytes_received += len(chunk)
            
        # Stop timing the moment the transfer completes
        end_time = time.perf_counter()
        
    # --- Reporting ---
    duration = end_time - start_time
    
    # Calculate throughput in Megabits per second (Mbps)
    # 1 Byte = 8 bits
    # 1 Megabit = 1,000,000 bits (Standard SI networking unit)
    bits_received = bytes_received * 8
    throughput_mbps = (bits_received / 1_000_000) / duration
    
    print("\n--- First 320 Characters ---")
    print(first_320_bytes.decode('ascii', errors='replace'))
    
    print("\n--- Transfer Statistics ---")
    print(f"Total size received: {bytes_received} bytes")
    print(f"Time elapsed:        {duration:.4f} seconds")
    print(f"Throughput:          {throughput_mbps:.2f} Mbps")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TCP File Downloader (In-Memory)")
    parser.add_argument(
        "size", 
        type=int, 
        help="The size of the 'file' to download in bytes."
    )
    args = parser.parse_args()
    
    start_client(args.size)