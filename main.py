import os
import sys
import queue
import asyncio
import traceback

import discord

from util.logger import logger
from util.chat import Chat
from util.keep_alive import keep_alive

from itertools import cycle

from discord.ext import tasks, commands

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN') # Put yor Discord bot token here
DISCORD_AVAL_CHANNELS = [123456789] # Put in yor channel IDs

bot = commands.Bot(command_prefix='#', intents=discord.Intents.all())

msg_que = queue.Queue()

status = cycle(['A', 'B'])


async def use_gpt(chat):
  try:
    while True:
      if not msg_que.empty():
        message = msg_que.get()

        async with message.channel.typing():
          content = chat.talk(message.content)

        if content != '':
          await message.reply(content)

        await asyncio.sleep(3.5)

        await chat.do_abstract()

      await asyncio.sleep(0.5)

  except Exception as e:
    logger.error(traceback.print_exc())
    logger.error(str(e))

    embed = discord.Embed(title='ERROR', description=e, color=0xEB4034)
    await message.channel.send(embed=embed)

    os.execv(sys.executable, ['python'] + sys.argv)


@bot.command()
async def reboot(ctx):
  embed = discord.Embed(title='REBOOT', color=0xEB4034)
  await ctx.send(embed=embed)
  os.execv(sys.executable, ['python'] + sys.argv)


@tasks.loop(seconds=10)
async def change_status():
  await bot.change_presence(activity=discord.Game(next(status)))


@bot.event
async def on_message(message):
  await bot.process_commands(message)
  
  if message.author == bot.user:
    return
  elif message.channel.id not in DISCORD_AVAL_CHANNELS:
    return
  elif message.content.startswith('#'):
    return

  prefix = f'<@{message.author.id}>：' # Enabling the bot to identify the sender of a message
  message.content = prefix + message.content
  msg_que.put(message)


@bot.event
async def on_ready():
  logger.info(f'Bot is logged in as {bot.user}')

  change_status.start()

  chat = Chat()
  chat.init()

  asyncio.create_task(use_gpt(chat))


def main():
  bot.run(DISCORD_TOKEN, log_handler=None)


if __name__ == '__main__':
  keep_alive()
  main()
