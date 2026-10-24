import socket
import sys
import time
import struct
import random

# Configuration
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12000
MAX_UDP_PAYLOAD = 65535

def create_packet(pkt_type, seq, payload=b""):
    # Header: 1 byte type, 1 byte sequence, 2 bytes length
    header = struct.pack('!BBH', pkt_type, seq, len(payload))
    return header + payload

def parse_packet(packet):
    header = packet[:4]
    pkt_type, seq, payload_len = struct.unpack('!BBH', header)
    payload = packet[4:4+payload_len]
    return pkt_type, seq, payload

def run_client(file_size, timeout, data_loss_prob, ack_loss_prob):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(timeout)
    
    # Construct REQ packet payload
    req_payload = f"{file_size},{timeout},{ack_loss_prob}".encode('utf-8')
    req_packet = create_packet(0, 0, req_payload)
    
    print(f"Initiating request to {SERVER_HOST}:{SERVER_PORT}")
    print(f"Parameters -> Size: {file_size:,} bytes | Timeout: {timeout}s | Data Loss Prob: {data_loss_prob} | ACK Loss Prob: {ack_loss_prob}\n")
    
    # Start timer from the moment the initial REQ is sent
    start_time = time.perf_counter()
    
    # 1. Reliable Request Phase
    while True:
        client_socket.sendto(req_packet, (SERVER_HOST, SERVER_PORT))
        try:
            packet, _ = client_socket.recvfrom(MAX_UDP_PAYLOAD)
            pkt_type, _, _ = parse_packet(packet)
            if pkt_type == 1: # RAK received
                print("Server acknowledged request (RAK). Data transfer started...\n")
                break
        except socket.timeout:
            print("[!] Timeout waiting for server RAK. Retransmitting REQ...")

    # 2. Data Transfer Phase (Stop-and-Wait ARQ)
    first_1040_bytes = bytearray()
    bytes_received = 0
    expected_seq = 0
    
    # Remove timeout constraint; server handles retransmission timeouts
    client_socket.settimeout(None) 
    
    while bytes_received < file_size:
        packet, _ = client_socket.recvfrom(MAX_UDP_PAYLOAD)
        pkt_type, seq, payload = parse_packet(packet)
        
        if pkt_type == 2: # DAT packet
            # Simulate Data Loss
            if random.random() < data_loss_prob:
                print(f"[*] Simulated drop of DAT packet (Seq: {seq})")
                continue # Ignore packet without sending ACK
                
            if seq == expected_seq:
                # New in-order data packet
                if len(first_1040_bytes) < 1040:
                    needed = 1040 - len(first_1040_bytes)
                    first_1040_bytes.extend(payload[:needed])
                    
                bytes_received += len(payload)
                expected_seq = 1 - expected_seq # Flip expected sequence (0 <-> 1)
            else:
                # Duplicate packet received (Server retransmitted because ACK was lost)
                print(f"[!] Duplicate DAT packet (Seq: {seq}) received. Dropping payload, re-sending ACK.")
                
            # Send ACK for the received packet's sequence number
            ack_packet = create_packet(3, seq)
            client_socket.sendto(ack_packet, (SERVER_HOST, SERVER_PORT))

    # Stop timer when the complete file is received
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    # --- Throughput Calculations ---
    total_bits = bytes_received * 8
    throughput_bps = total_bits / duration if duration > 0 else 0
    throughput_mbps = throughput_bps / 1_000_000  # Convert bits/sec to Megabits/sec (Mbps)
    
    # Display Results
    print("=" * 50)
    print("                TRANSFER SUMMARY                ")
    print("=" * 50)
    print(f"First 1040 characters:\n{first_1040_bytes.decode('utf-8', errors='replace')}\n")
    print(f"Total Bytes Received : {bytes_received:,} bytes")
    print(f"Total Bits Received  : {total_bits:,} bits")
    print(f"Total Transfer Time  : {duration:.4f} seconds")
    print(f"Throughput           : {throughput_mbps:.4f} Mbps")
    print("=" * 50)

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("Usage: python client.py <file_size_bytes> <timeout_sec> <data_loss_prob> <ack_loss_prob>")
        print("Example: python client.py 10485760 0.2 0.1 0.05")
        sys.exit(1)
        
    try:
        requested_size = int(sys.argv[1])
        timeout_val = float(sys.argv[2])
        data_loss = float(sys.argv[3])
        ack_loss = float(sys.argv[4])
        
        if requested_size <= 0 or timeout_val <= 0:
            raise ValueError("Size and timeout must be > 0.")
        if not (0.0 <= data_loss <= 0.8) or not (0.0 <= ack_loss <= 0.8):
            raise ValueError("Loss probabilities must be between 0.0 and 0.8.")
            
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
        
    run_client(requested_size, timeout_val, data_loss, ack_loss)