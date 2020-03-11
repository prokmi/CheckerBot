import os

from discord.ext.commands import Bot
import logging

from armory import ArmoryAPI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('CheckerBot')

TOKEN = os.environ['DISCORD_KEY']
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


@bot.command()
async def pomoc(ctx):
    await ctx.send("__Dostupné příkazy:__ \n"
                   "**++pomoc** - zobrazí dostupné příkazy \n"
                   "**++zkontroluj** _postava_ _realm_ - zkontroluje enchanty a gemy dané postavy. Jméno realmu pište jednoslovně a ideálně camelcase. "
                   "V případě, že se jedná o Drak'thul, se realm vyplňovat nemusí vůbec. Pokud je postava na Burning Blade a neexistuje na Drak'thulu, tak taky ne.\n"
                   "**++zkontrolujobe** _postava_ - zkontroluje stejnou postavu jak na Drak'thulu, tak na Burning Blade\n"
                   "**++inspekce** - zkontroluje raid sestavu, jestli má vše v pořádku\n"
                   )


@bot.command()
async def inspekce(ctx):
    await ctx.send(armory.check_members())


@bot.command()
async def zkontrolujobe(ctx, jmeno: str):
    await ctx.send(armory.find_char_on_both_realms(jmeno))


@bot.command()
async def snemovna(ctx):
    await ctx.send(armory.print_corruption())


@bot.command()
async def korupce(ctx):
    await ctx.send(armory.print_corruption())

bot.run(TOKEN)
