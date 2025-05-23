import socket

# Configuration
IP = "192.168.10.1"
PORT = 10000
COMMAND = b'E'  # ASCII 'E'

# Create a TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    sock.connect((IP, PORT))
    sock.sendall(COMMAND)
    
    response = sock.recv(1024)  # Receive up to 1024 bytes
    
    print("Raw Response (Hex):", response.hex())

    if len(response) >= 45:
        # Extract relevant fields from the response
        mode = response[5]
        group_number = response[10]
        mute_status = response[11]
        stop_status = response[12]
        pattern_number = response[13]
        
        tier1_status = response[14]
        tier2_status = response[15]
        tier3_status = response[16]
        tier4_status = response[17]
        tier5_status = response[18]
        
        buzzer_pattern = response[19]

        # Print interpreted results
        print(f"Mode: {'Smart Mode' if mode == 0x01 else 'Signal Tower Mode'}")
        print(f"Smart Mode Group Number: {group_number}")
        print(f"Mute: {'On' if mute_status == 0x01 else 'Off'}")
        print(f"STOP: {'On' if stop_status == 0x01 else 'Off'}")
        print(f"Pattern Number: {pattern_number}")
        print(f"Tier 1: {['Off', 'On', 'Flashing'][tier1_status]}")
        print(f"Tier 2: {['Off', 'On', 'Flashing'][tier2_status]}")
        print(f"Tier 3: {['Off', 'On', 'Flashing'][tier3_status]}")
        print(f"Tier 4: {['Off', 'On', 'Flashing'][tier4_status]}")
        print(f"Tier 5: {['Off', 'On', 'Flashing'][tier5_status]}")
        print(f"Buzzer Pattern: {buzzer_pattern}")

finally:
    sock.close()
