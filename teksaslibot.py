import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

music_queue = []
current_song = None
is_paused = False

# YTDL
ytdl_format_options = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
}

ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.title = data.get("title")

    @classmethod
    async def from_url(cls, url):
        loop = asyncio.get_event_loop()

        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=False)
        )

        if "entries" in data:
            data = data["entries"][0]

        return cls(
            discord.FFmpegPCMAudio(data["url"], **ffmpeg_options),
            data=data,
        )


@bot.event
async def on_ready():
    print(f"Bot hazır: {bot.user}")


async def play_next(ctx):
    global current_song, is_paused

    if music_queue:
        current_song = music_queue.pop(0)
        is_paused = False

        ctx.voice_client.play(
            current_song,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                play_next(ctx), bot.loop
            ),
        )

        await ctx.send(f"🎵 Şimdi çalıyor: **{current_song.title}**")
    else:
        current_song = None


# 🎵 ŞARKI
@bot.command(name="şarkı")
async def play(ctx, *, search):

    if not ctx.author.voice:
        return await ctx.send("Önce ses kanalına gir.")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    player = await YTDLSource.from_url(search)
    music_queue.append(player)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)
    else:
        await ctx.send(f"📋 Kuyruğa eklendi: **{player.title}**")


# ⏹ DUR
@bot.command()
async def kapat(ctx):

    global current_song, is_paused

    if ctx.voice_client:
        ctx.voice_client.stop()
        music_queue.clear()
        current_song = None
        is_paused = False
        await ctx.send("⏹️ Müzik durduruldu.")


# ⏸ DURAKLAT
@bot.command()
async def durdur(ctx):

    global is_paused

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        is_paused = True
        await ctx.send("⏸️ Duraklatıldı.")


# ▶ DEVAM
@bot.command()
async def devam(ctx):

    global is_paused

    if ctx.voice_client and is_paused:
        ctx.voice_client.resume()
        is_paused = False
        await ctx.send("▶️ Devam ediyor.")


# ⏭ ATLA
@bot.command()
async def atla(ctx):

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Atlandı.")


# 📊 PING
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)} ms")


# ❌ HATA
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Komut yok.")
    else:
        await ctx.send(f"Hata: {error}")


# START
bot.run(os.getenv("TOKEN"))
