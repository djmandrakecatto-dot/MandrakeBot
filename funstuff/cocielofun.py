import asyncio
import base64
import io
import time
import weakref
from typing import List
import json

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
import subprocess
import tempfile
import os

# Replace with your actual emoji IDs or keep unicode
EMOJI_CRY = "😢"   # or "<:lori_chorando:ID>"
EMOJI_RAGE = "😣"

class CocieloChavesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._http: aiohttp.ClientSession = None
        # map guild_id -> (asyncio.Lock, last_access_timestamp)
        self._guild_locks = {}

    async def cog_load(self):
        self._http = aiohttp.ClientSession()

    async def cog_unload(self):
        await self._http.close()

    def get_lock(self, guild_id: int) -> asyncio.Lock:
        """Return a per-guild lock with 60s expire-after-access semantics."""
        now = time.time()
        entry = self._guild_locks.get(guild_id)
        if entry is None:
            lock = asyncio.Lock()
            self._guild_locks[guild_id] = (lock, now)
            return lock

        lock, last = entry
        # expire after 60 seconds of inactivity
        if now - last > 60:
            lock = asyncio.Lock()
            self._guild_locks[guild_id] = (lock, now)
            return lock

        # update last access
        self._guild_locks[guild_id] = (lock, now)
        return lock

    async def get_avatar_base64(self, user: discord.User) -> str:
        """Fetch user avatar directly from Discord CDN and return base64 data URI."""
        
        # Se tiver avatar custom
        if user.avatar:
            avatar_hash = user.avatar.key  # hash real
            avatar_url = f"https://cdn.discordapp.com/avatars/{user.id}/{avatar_hash}.png?size=512"
        else:
            # Avatar padrão do Discord (0-5)
            default_index = int(user.discriminator) % 5 if user.discriminator != "0" else (user.id >> 22) % 6
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"

        async with self._http.get(avatar_url) as resp:
            if resp.status != 200:
                raise ValueError(f"Failed to fetch avatar from CDN ({resp.status})")

            data = await resp.read()
            b64 = base64.b64encode(data).decode()
            # return raw base64 (server expects base64 string, not data URI)
            return b64
        
    def get_avatar_url(self, user: discord.User) -> str:
        """Return stable Discord CDN avatar URL."""
        
        if user.avatar:
            avatar_hash = user.avatar.key
            return f"https://cdn.discordapp.com/avatars/{user.id}/{avatar_hash}.png?size=256"
        else:
            # Avatar padrão
            default_index = (user.id >> 22) % 6
            return f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"

    @commands.hybrid_command(
        name="cocielochaves",
        aliases=["cocielo", "chavescocielo", "gang", "gangue"],
        description="Cria um vídeo meme Cocielo + Chaves com avatares dos seus amigos da quebrada!"
    )
    @app_commands.describe(
        users="Mencione até 5 usuários (@user) ou cole os IDs separados por espaço"
    )
    @commands.cooldown(1, 45, commands.BucketType.guild)
    @commands.guild_only()
    async def cocielochaves(self, ctx: commands.Context, *, users: str = None):
        lock = self.get_lock(ctx.guild.id)

        if lock.locked():
            await ctx.send(f"Já tem um vídeo sendo gerado aqui {EMOJI_CRY}")
            return

        async with lock:
            # Parse users: mentions first, then split IDs from the string
            members = []
            if ctx.message.mentions:
                mentions = [m for m in ctx.message.mentions if not m.bot]
                if len(mentions) > 5:
                    members = mentions[:5]
                    await ctx.send("Limitei aos primeiros 5 usuários mencionados. Use no máximo 5 usuários.")
                else:
                    members = mentions[:5]

            if not members and users:
                # Try parsing as space-separated IDs (limit to first 5 tokens)
                parts = users.split()
                if len(parts) > 5:
                    parts = parts[:5]
                    await ctx.send("Limitei aos primeiros 5 IDs fornecidos. Use no máximo 5 usuários.")

                for part in parts:
                    try:
                        uid = int(part.strip())
                        user = await self.bot.fetch_user(uid)
                        members.append(user)
                    except (ValueError, discord.NotFound):
                        continue
                members = members[:5]

            usage = (
                "Mencione os usuários ou cole os IDs!\n\n"
                "**Exemplo:**\n"
                "`cocielochaves @Denilson @Amigo1 @Amigo2`\n"
                "ou\n"
                "`cocielochaves 297153970613387264 159985870458322944`\n\n"
                "Usa os avatares para fazer a edição Chaves Cocielo! 🚀"
            )

            # Kotlin behavior: expects 5 images. If none provided, show usage.
            if not members:
                await ctx.send(usage)
                return
            # If there is at least one member, proceed — we'll fill missing slots
            # with Discord default avatars so the API always receives up to 5 images.
            await ctx.defer()

            images_payload = []

            # First, include any image attachments from the message (as base64)
            attachments = getattr(ctx.message, "attachments", []) or []
            if attachments and len(attachments) > 5:
                await ctx.send("Limitei aos primeiros 5 anexos. Use no máximo 5 imagens.")

            for att in attachments[:5]:
                if len(images_payload) >= 5:
                    break
                try:
                    async with self._http.get(att.url) as resp:
                        if resp.status != 200:
                            print(f"Falha ao baixar anexo {att.url}: {resp.status}")
                            continue
                        data = await resp.read()
                        b64 = base64.b64encode(data).decode()
                        images_payload.append({"type": "base64", "content": b64})
                except Exception as e:
                    print("Falha ao buscar anexo:", e)

            # Then include avatars from mentioned users / IDs until we reach 5 images
            for member in members:
                if len(images_payload) >= 5:
                    break
                try:
                    b64 = await self.get_avatar_base64(member)
                    if b64:
                        images_payload.append({"type": "base64", "content": b64})
                except Exception as e:
                    print("Falha avatar:", e)

            # If none of the provided members yielded avatars, fail.
            if not images_payload:
                await ctx.send(f"Não consegui achar imagens válidas {EMOJI_CRY}")
                return

            # Fill remaining slots (up to 5) with Discord default embed avatars as URLs
            i = 0
            while len(images_payload) < 5:
                default_index = i % 6
                url = f"https://cdn.discordapp.com/embed/avatars/{default_index}.png"
                images_payload.append({"type": "url", "content": url})
                i += 1

            payload = {"images": images_payload}
            print("Enviando payload:", payload)

            try:
                print("===== DEBUG INICIO =====")
                print("Enviando payload:", payload)

                # write payload to a temporary JSON file and call Java CLI
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8")
                try:
                    json.dump(payload, tmp)
                    tmp_path = tmp.name
                finally:
                    tmp.close()

                # compile Java CLI if needed
                java_src = os.path.join(os.getcwd(), "tools", "CocieloChaves.java")
                class_file = os.path.join(os.getcwd(), "tools", "CocieloChaves.class")
                if not os.path.exists(class_file):
                    print("Compilando Java CLI...")
                    p = await asyncio.create_subprocess_exec("javac", java_src, cwd=os.getcwd(), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                    out, err = await p.communicate()
                    if p.returncode != 0:
                        print("javac failed:", err.decode(errors="ignore"))
                        await ctx.send("Erro ao compilar a ferramenta Java. Certifique-se de que o JDK está instalado.")
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass
                        return
                # run Java CLI and capture stdout (binary video)
                proc = await asyncio.create_subprocess_exec("java", "-cp", os.path.join(os.getcwd(), "tools"), "CocieloChaves", tmp_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                try:
                    stdout, stderr = await proc.communicate()
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

                if proc.returncode == 2:
                    print("Client error from API:", stderr.decode(errors="ignore"))
                    await ctx.send(f"Erro cliente ao gerar vídeo {EMOJI_CRY}")
                    return
                elif proc.returncode != 0:
                    print("Error from Java tool (code", proc.returncode, "):", stderr.decode(errors="ignore"))
                    await ctx.send(f"Erro ao gerar vídeo {EMOJI_RAGE} {EMOJI_CRY}")
                    return

                video_data = stdout
                print("Vídeo recebido com sucesso")
                print("===== DEBUG FIM =====")

            except asyncio.TimeoutError:
                print("TIMEOUT ACONTECEU")
                await ctx.send("Demorou muito... tente novamente depois 😔")
                return

            except Exception as e:
                print("ERRO INESPERADO:", repr(e))
                await ctx.send(f"Erro inesperado: {e}")
                return

            file = discord.File(io.BytesIO(video_data), "cocielo_chaves.mp4")

            await ctx.send(
                f"Pronto! Sua gangue da quebrada: {' '.join(m.mention for m in members)}",
                file=file
            )


async def setup(bot):
    await bot.add_cog(CocieloChavesCog(bot))