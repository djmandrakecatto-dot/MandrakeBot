import socket
import struct
import random
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad, pad

# Configuration
SERVER_IP = "127.0.0.1"
PORT = 4444
SECRET_KEY = b'SixteenByteKey!!'

# All 27 Opcodes
CMDS = {
    "GET": 0x01, "POST": 0x02, "TRY": 0x03, "EXCEPT": 0x04,
    "SEND": 0x05, "RECEIVE": 0x06, "MODIFY": 0x07, "HEARTBEAT": 0x08,
    "SHUTDOWN": 0x09, "CALL_FUNC": 0x0A, "DEFINE_FUNC": 0x0B,
    "PUSH_STACK": 0x0C, "POP_STACK": 0x0D, "SET_VAR": 0x0E,
    "GET_VAR": 0x0F, "READ_ONLY": 0x10, "READ_WRITE": 0x11,
    "DELETE_VAR": 0x12, "LOCK_VAR": 0x13, "UNLOCK_VAR": 0x14,
    "ALLOC_MEM": 0x15, "FREE_MEM": 0x16, "READ_BYTE": 0x17,
    "WRITE_BYTE": 0x18, "EXEC_HEX": 0x19, "DUMP_REGS": 0x1A,
    "SET_PTR": 0x1B
}

current_maze_binary = bytearray()

def decrypt_payload(data):
    iv = data[:16]
    cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(data[16:]), AES.block_size)

# Fixed: Accepts width and height for exactly 800 bytes
def generate_maze(w, h):
    # Generates binary maze: 0x00=Wall, 0x01=Path
    return bytearray([random.choices([0, 1], weights=[30, 70])[0] for _ in range(w * h)])

def run_server():
    global current_maze_binary
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, PORT))
    print(f"[*] HTTP/4 Binary Server listening on {PORT} (Little-Endian)...")

    while True:
        try:
            data, addr = sock.recvfrom(8192)
            # Unpack Header <BBI
            is_ret, opcode, length = struct.unpack('<BBI', data[:6])
            
            # Response logic
            response_payload = b"OK"
            
            if opcode == CMDS["CALL_FUNC"]: 
                # 20 * 40 = 800 bytes exactly
                current_maze_binary = generate_maze(20, 40)
                response_payload = current_maze_binary
                print(f"[!] Success: Generated {len(current_maze_binary)} bytes.")
            elif opcode == CMDS["GET_VAR"]:
                response_payload = current_maze_binary if current_maze_binary else b"EMPTY"

            elif opcode == CMDS["MODIFY"]:
                # Decrypting only if the opcode is 0x07
                payload = data[6:6+length]
                decrypted = decrypt_payload(payload)
                print(f"[*] Secure Modification: {decrypted}")
                response_payload = b"MODIFIED"

            # Build Return Packet: [Return=1][Opcode][Len][Payload][END][ID]
            header = struct.pack('<BBI', 1, opcode, len(response_payload))
            footer = b"END" + struct.pack('<I', 2026)
            sock.sendto(header + response_payload + footer, addr)
            
        except Exception as e:
            print(f"Server Error: {e}")

if __name__ == "__main__":
    run_server()