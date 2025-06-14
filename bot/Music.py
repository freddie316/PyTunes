"""
Author: freddie316
Date: Sun Mar 26 2023
"""

import os
import validators
import asyncio
import yt_dlp
import discord
from discord.ext import commands, tasks
from gtts import gTTS
from pathlib import Path

ytdl_format_options = {
    "format": "m4a/bestaudio/best",
    "outtmpl": "%(title)s.%(ext)s",
    "noplaylist": True,
    "default_search": "ytsearch3", 
    "postprocessors": [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'm4a'
    }],
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

ffmpeg_options = {"options": "-vn"}

lang = 'en'
accent = 'us'
speech = {"join.m4a":"Ready and waiting."}

class Music(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot
        self.repeatFlag = False
        self.busy = False
        self.leavingAudioFlag = False
        self.queue = []
        self.audPath = Path('.').resolve().parent / 'Audio'
        for trigger in speech:
            if not os.path.isfile(self.audPath / trigger):
                tts = gTTS(speech[trigger],lang=lang,tld=accent)
                tts.save(self.audPath / trigger)

        
    @commands.command()
    async def join(self, ctx):
        """Joins your current voice channel"""
        try:
            channel = ctx.author.voice.channel
        except:
            await ctx.reply("Are you in voice channel?")
            return
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
            self.afk_timer.restart()
            return
        try:
            await channel.connect(timeout=15.0,reconnect=True)
            print(f"Connected to {channel}")

        except Exception as e:
            print("Failed to connect: " + e)

        else:
            self.afk_timer.start()
            """
            filename = list(speech.keys())[0]
            audio = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.audPath / filename, **ffmpeg_options))
            ctx.voice_client.play(audio)
            """

    @commands.command()
    async def leave(self, ctx):
        """Exits the current voice channel"""
        try:
            if ctx.voice_client.is_playing():
                await self.stop(ctx)
            print(f"Disconnected from {ctx.voice_client.channel}")
            await ctx.voice_client.disconnect()
        except:
            await ctx.reply("I'm not connected to a voice channel.")
            return
        self.afk_timer.cancel()

    @commands.command()
    async def play(self, ctx, query):
        """Plays the audio from the provided youtube link or searches youtube for the provided song title"""
        
        self.busy = True # begin busy state - prevent afk timer from disconnecting
        
        try:
            async with ctx.typing():
                if ctx.voice_client is None:
                    await self.join(ctx)
                if validators.url(query): # true if input is an actual url
                    await self.prepare_song(ctx,query)
                else:
                    # Begin search for video
                    source = ytdl.extract_info(query,download=False)
                    guesses = []
                    for entry in source['entries']:
                        guesses.append(entry['title'])
                    msg = await ctx.reply(
                        f'''I've found three songs that match your search. Please pick one:\n
                        1. {guesses[0]}\n
                        2. {guesses[1]}\n
                        3. {guesses[2]}\n'''
                    )
                    reactions = ['1️⃣','2️⃣','3️⃣','❌']
                    for emoji in reactions:
                        await msg.add_reaction(emoji)
                    def check(react,user):
                        return react.emoji in reactions and user == ctx.author
                    response = await self.bot.wait_for(
                        "reaction_add",
                        check=check
                    )
                    reaction = response[0].emoji
                    if reaction == '❌':
                        await ctx.reply(f"Canceling.")
                        return
                    choice = source['entries'][reactions.index(reaction)]['webpage_url']
                    await self.prepare_song(ctx,choice)
        except Exception as e:
            await ctx.reply(f"An error occured: {e}")
            
        self.busy = False # end busy state

    async def prepare_song(self,ctx,query):
        """Function for handling file preparation before playing""" 
        source = ytdl.extract_info(query,download=True)
        filename = source['requested_downloads'][0]['filepath']
        
        if ctx.voice_client.is_playing():
            self.queue.append(filename)
            await ctx.reply(f"Added to queue: {source['title']}")
            return
        
        song = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename, **ffmpeg_options))
        ctx.voice_client.play(song,
            after = lambda e: self.clean_up(ctx, filename)
        )
        await ctx.reply(f"Now playing: {source['title']}")

    def clean_up(self, ctx, filename):
        """Function for handling the aftermath of playing a song"""
        if self.repeatFlag:
            song = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename, **ffmpeg_options))
            ctx.voice_client.play(song,
                after = lambda e: self.clean_up(ctx,filename)
            )
        elif self.queue:
            os.remove(filename)
            filename = self.queue.pop(0)
            song = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(filename, **ffmpeg_options))
            ctx.voice_client.play(song,
                after = lambda e: self.clean_up(ctx,filename)
            )
        else:
            os.remove(filename)
        
        self.afk_timer.restart()
     
    @commands.command()
    async def repeat(self, ctx):
        """Turns on/off repeat for the current song"""
        if self.repeatFlag:
            self.repeatFlag = False
        else:
            self.repeatFlag = True
        await ctx.reply(f"Repeat mode: {self.repeatFlag}")
        
    @commands.command()
    async def idleAudio(self, ctx):
        """Turns on/off the funny leave sound"""
        if self.leavingAudioFlag:
            self.leavingAudioFlag = False
            await ctx.reply(f"Disabled idle disconnect audio")
        else:
            self.leavingAudioFlag = True
            await ctx.reply(f"Enabled idle disconnect audio")
    
    @commands.command()
    async def stop(self, ctx):
        """Stops playing the current song"""
        if ctx.voice_client is None:
            await ctx.reply("I'm not connected to a voice channel.")  
            return
        if not ctx.voice_client.is_playing():
            await ctx.reply("I'm not playing anything.")  
            return
        if self.repeatFlag:
            self.repeatFlag = False
            ctx.voice_client.stop()
        else:
            ctx.voice_client.stop()
    
    @tasks.loop(seconds = 0) # 5 minute timer, Not implemented here since the code will execute immediately then wait till the next loop 
    async def afk_timer(self):
        await asyncio.sleep(300) # 300s - wait 5 minutes before executing idle code
        print(f"Checking AFK: Is Busy? {self.busy}")
        if self.busy: # exit idle timer early if bot is busy
            return
        
        if not self.bot.voice_clients: # exit idle timer early if there are no vc's
            self.afk_timer.cancel()
            return
        
        for vc in self.bot.voice_clients: # check each vc to see if should be dc'd
            if not vc.is_playing() and not self.busy:
                if self.leavingAudioFlag:
                    song = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.audPath / 'leaving.m4a', **ffmpeg_options))
                    vc.play(song)
                    await asyncio.sleep(3)
                await vc.disconnect()
                print(f"Disconnected from {vc.channel}")
                self.afk_timer.cancel()
        return

async def setup(bot):
    await bot.add_cog(Music(bot))
    
def main():

    return

if __name__ == "__main__":
    main()