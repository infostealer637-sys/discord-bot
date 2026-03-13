import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

music_queue = []
current_song = None
is_paused = False

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
    async def from_url(cls, url, *, loop=None):

        loop = loop or asyncio.get_event_loop()

        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=False)
        )

        if "entries" in data:
            data = data["entries"][0]

        return cls(
            discord.FFmpegPCMAudio(
                data["url"], **ffmpeg_options
            ),
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


# ---------------- MUSIC ----------------

@bot.command(name="şarkı")
async def play(ctx, *, search):

    if not ctx.author.voice:
        return await ctx.send("Önce ses kanalına gir.")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    player = await YTDLSource.from_url(search, loop=bot.loop)
    music_queue.append(player)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)
    else:
        await ctx.send(f"📋 Kuyruğa eklendi: **{player.title}**")


@bot.command(name="sıra")
async def show_queue(ctx):

    if not music_queue and not current_song:
        return await ctx.send("Kuyruk boş.")

    msg = ""

    if current_song:
        msg += f"▶️ Şu an çalıyor: {current_song.title}\n\n"

    if music_queue:
        msg += "📋 Sıradakiler:\n"
        for i, song in enumerate(music_queue):
            msg += f"{i+1}. {song.title}\n"

    await ctx.send(msg)


@bot.command(name="kapat")
async def stop(ctx):

    global current_song, is_paused

    if ctx.voice_client:
        ctx.voice_client.stop()
        music_queue.clear()
        current_song = None
        is_paused = False
        await ctx.send("⏹️ Müzik durduruldu.")


@bot.command(name="durdur")
async def pause(ctx):

    global is_paused

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        is_paused = True
        await ctx.send("⏸️ Duraklatıldı.")


@bot.command(name="devam")
async def resume(ctx):

    global is_paused

    if ctx.voice_client and is_paused:
        ctx.voice_client.resume()
        is_paused = False
        await ctx.send("▶️ Devam ediyor.")


@bot.command(name="çık")
async def leave(ctx):

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        music_queue.clear()


@bot.command(name="atla")
async def skip(ctx):

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Atlandı.")


# ---------------- MODERATION ----------------

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):

    await member.kick(reason=reason)
    await ctx.send(f"{member} atıldı.")


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):

    await member.ban(reason=reason)
    await ctx.send(f"{member} yasaklandı.")


@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):

    role = discord.utils.get(ctx.guild.roles, name="Muted")

    if not role:
        role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, speak=False, send_messages=False)

    await member.add_roles(role)
    await ctx.send(f"{member} susturuldu.")


@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):

    role = discord.utils.get(ctx.guild.roles, name="Muted")
    if role:
        await member.remove_roles(role)

    await ctx.send(f"{member} susturması kaldırıldı.")


# ---------------- UTILITY ----------------

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)} ms")


@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):

    await ctx.channel.purge(limit=amount + 1)
    await ctx.send("Mesajlar silindi.")


@bot.command()
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(title="Kullanıcı Bilgisi")
    embed.add_field(name="İsim", value=member.name)
    embed.add_field(name="ID", value=member.id)
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)


# ---------------- ERROR ----------------

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Komut yok. !yardım yaz.")
    else:
        await ctx.send(f"Hata: {error}")


# ---------------- START ----------------


bot.run(os.getenv("TOKEN"))
