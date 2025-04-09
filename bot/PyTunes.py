"""
Author: freddie316
Date: Thu Mar 16 2023
"""

version = "2.0.1"

# Module Imports
import os
import sys
import asyncio
import traceback
import discord
from discord.ext import commands
from dotenv import load_dotenv

cogs = ["Music","Fun"]

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!',intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} is connected to the following guild:\n')
    for guild in bot.guilds:
        print(f'{guild.name} (id: {guild.id})\n')
        
@bot.event
async def on_error(event, *args, **kwargs):
    print(event)

@bot.event
async def on_command_error(ctx,error):
    print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

@bot.command()
async def ping(ctx):
    """Pong!"""
    await ctx.reply("Pong!") 

@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    """Bot owner only, closes the bot's connection with discord"""
    print("Beginning shutdown")
    await ctx.reply("Shutting down.")
    try:
        if ctx.voice_client.is_playing():
            await bot.stop(ctx)
    finally:
        for vc in bot.voice_clients:
            await vc.disconnect()
            print(f"Disconnected from {vc.channel}")
        await bot.close()

@bot.command()
@commands.is_owner()
async def reload(ctx):
    """Bot owner only, reloads cogs to facilitate editing without downtime"""
    print(f"Reloading cogs...")
    async with ctx.typing():
        message = await ctx.reply(f"Reloading cogs...")
        try:
            for cog in cogs:
                await bot.reload_extension(cog)
        except Exception as e:
            print(f"Reload failed")
            await message.edit(content=f"An error occured: {e}")
        else:
            print(f"Reload complete")
            await message.edit(content=f"Reload complete!")

async def main():
    async with bot:
        for cog in cogs:
            await bot.load_extension(cog)
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
