import socket
import struct
import sys
import random

# Configuration
HOST = '127.0.0.1'
PORT = 12000
PATTERN_CYCLE = b''.join([bytes([ord('a') + i]) * 80 for i in range(26)])
CHUNK_SIZE = len(PATTERN_CYCLE) * 2 # 4160 bytes

def create_packet(pkt_type, seq, payload=b""):
    header = struct.pack('!BBH', pkt_type, seq, len(payload))
    return header + payload

def parse_packet(packet):
    header = packet[:4]
    pkt_type, seq, payload_len = struct.unpack('!BBH', header)
    payload = packet[4:4+payload_len]
    return pkt_type, seq, payload

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((HOST, PORT))
    print(f"Server listening on {HOST}:{PORT}")
    print("Press Ctrl+C to shut down.")
    
    base_chunk = PATTERN_CYCLE * 2
    
    try:
        while True:
            server_socket.settimeout(1.0) 
            
            try:
                packet, client_address = server_socket.recvfrom(65535)
                pkt_type, _, payload = parse_packet(packet)
            except socket.timeout:
                continue
            except Exception:
                continue
                
            if pkt_type != 0: # Must be REQ
                continue
                
            try:
                req_data = payload.decode('utf-8').split(',')
                file_size = int(req_data[0])
                timeout = float(req_data[1])
                ack_loss_prob = float(req_data[2])
                print(f"\nREQ from {client_address}: Size={file_size}b, Timeout={timeout}s, ACK Loss Prob={ack_loss_prob}")
            except (ValueError, IndexError):
                print("Invalid request format.")
                continue
                
            # Send RAK (Request Acknowledgment) - Never dropped
            rak_packet = create_packet(1, 0)
            server_socket.sendto(rak_packet, client_address)
            
            server_socket.settimeout(timeout)
            
            bytes_sent = 0
            seq = 0
            
            while bytes_sent < file_size:
                remaining = file_size - bytes_sent
                send_size = min(CHUNK_SIZE, remaining)
                chunk = base_chunk[:send_size]
                
                data_packet = create_packet(2, seq, chunk)
                
                # Initial transmission
                server_socket.sendto(data_packet, client_address)
                
                ack_received = False
                while not ack_received:
                    try:
                        ack_packet, _ = server_socket.recvfrom(65535)
                        ack_type, ack_seq, _ = parse_packet(ack_packet)
                        
                        if ack_type == 3: # ACK packet
                            # Simulate ACK Loss
                            if random.random() < ack_loss_prob:
                                print(f"[*] Simulated drop of ACK {ack_seq}")
                                continue # Go back to waiting for an ACK, will eventually trigger timeout
                                
                            if ack_seq == seq:
                                ack_received = True 
                                
                    except socket.timeout:
                        print(f"[!] Timeout waiting for ACK {seq}. Retransmitting DAT {seq}...")
                        server_socket.sendto(data_packet, client_address)
                    except ConnectionResetError:
                        print("Client disconnected unexpectedly.")
                        break
                        
                if not ack_received:
                    break 
                    
                bytes_sent += send_size
                seq = 1 - seq 
                
            print(f"Transfer complete: {bytes_sent} bytes sent.")
            print("\nWaiting for client request...")
            
    except KeyboardInterrupt:
        print("\nCtrl+C detected. Shutting down server gracefully...")
    finally:
        server_socket.close()
        sys.exit(0)

if __name__ == '__main__':
    start_server()