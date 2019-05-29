from discord.ext.commands import Bot
import logging

from __auth._auth import Auth
from armory import ArmoryAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('CheckerBot')

TOKEN = Auth.DISCORD_KEY
BOT_PREFIX = "++"
armory = ArmoryAPI()
bot = Bot(command_prefix=BOT_PREFIX)


@bot.event
async def on_ready():
    logger.info("Logged in as")
    logger.info(bot.user.name)
    logger.info(bot.user.id)
    logger.info('-'*20)


@bot.command()
async def zkontroluj(ctx, jmeno: str, realm: str = None):
    await ctx.send(armory.find_char(jmeno, realm))

bot.run(TOKEN)
