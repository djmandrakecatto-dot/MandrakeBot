import discord
from discord.ext import commands
import socket
import struct
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

class BinaryMazeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.SERVER_IP = "127.0.0.1"
        self.PORT = 4444
        self.SECRET_KEY = b'SixteenByteKey!!'
        self.CMDS = {
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

    def encrypt_payload(self, data):
        cipher = AES.new(self.SECRET_KEY, AES.MODE_CBC)
        return cipher.iv + cipher.encrypt(pad(data, AES.block_size))

    def send_http4_request(self, command_name, message, request_id=101):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        
        if isinstance(message, str):
            raw_payload = message.encode('utf-8')
        else:
            raw_payload = message
        
        cmd_id = self.CMDS.get(command_name, 0x01)
        
        if command_name == "MODIFY":
            raw_payload = self.encrypt_payload(raw_payload)

        # Header (Little-Endian: <)
        # [Return Flag (0)][Opcode][Payload Len]
        header = struct.pack('<BBI', 0, cmd_id, len(raw_payload))
        footer = b"END" + struct.pack('<I', request_id)
        
        try:
            sock.sendto(header + raw_payload + footer, (self.SERVER_IP, self.PORT))
            response, _ = sock.recvfrom(8192) # Buffer large enough for 800 bytes
            
            is_ret, ret_cmd, ret_len = struct.unpack('<BBI', response[:6])
            if is_ret == 1:
                return response[6:6+ret_len] # Raw Binary Payload (The 800 bytes)
        except:
            return None
        finally:
            sock.close()

    @commands.command()
    async def start_maze(self, ctx):
        """Requests 800 bytes and renders a 20x40 binary maze."""
        await ctx.send("📡 Fetching 800-byte binary stream...")
        binary_maze = self.send_http4_request("CALL_FUNC", "GEN_MAZE")
        
        if not binary_maze or len(binary_maze) != 800:
            err_len = len(binary_maze) if binary_maze else 0
            return await ctx.send(f"❌ Byte Error: Received {err_len}/800. Logic server might be misaligned.")

        # --- RENDERING ENGINE ---
        width = 20
        # Split into two parts to stay under Discord's 2000 character limit
        # Part 1: First 400 bytes (Rows 1-20)
        # Part 2: Next 400 bytes (Rows 21-40)
        
        chunks = [binary_maze[:400], binary_maze[400:]]
        
        for idx, chunk in enumerate(chunks):
            grid = ""
            for i, byte in enumerate(chunk):
                grid += "⬜" if byte == 1 else "⬛"
                if (i + 1) % width == 0:
                    grid += "\n"
            
            title = "Binary Maze (Top)" if idx == 0 else "Binary Maze (Bottom)"
            embed = discord.Embed(title=title, description=grid, color=0x00ff00)
            await ctx.send(embed=embed)

        await ctx.send("✅ 800 bytes processed successfully.")

async def setup(bot):
    await bot.add_cog(BinaryMazeCog(bot))