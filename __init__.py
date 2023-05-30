import random

from discord.ext import commands

import breadcord


class Yummy(breadcord.module.ModuleCog):
    @commands.hybrid_command(description='Roll a die with a min and max value')
    async def dice(self, ctx: commands.Context, value: int = 6, max_value: int = None):
        if max_value is None:
            value, max_value = 1, value
        await ctx.reply(f"Rolled a {random.randint(value, max_value)}! 🎲")


async def setup(bot: breadcord.Bot):
    await bot.add_cog(Yummy("yummy_toasts"))
