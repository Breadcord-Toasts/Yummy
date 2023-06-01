import random
import re

from discord.ext import commands

import breadcord


def dice_to_num(dice_roll: str) -> int | str:
    if not (match := re.match(r"^(?P<multiplier>\d*)d(?P<roll_max>\d+)", dice_roll)):
        return dice_roll

    roll_max = int(match["roll_max"])
    multiplier = int(match["multiplier"] or 1)
    roll_sum = sum(random.randint(1, roll_max) for _ in range(multiplier))

    return roll_sum


class Yummy(breadcord.module.ModuleCog):
    @commands.hybrid_command(description='Roll a die with a min and max value')
    async def dice(self, ctx: commands.Context, value: int = 6, max_value: int = None):
        if max_value is None:
            value, max_value = 1, value
        await ctx.reply(f"Rolled a {random.randint(value, max_value)}! 🎲")

    @commands.hybrid_command(description='Roll a die using dice notation')
    async def dnd_dice(self, ctx: commands.Context, *, dice_type: str = "1d6"):
        """
        Example of dice notation: "1d2", "1d20", "5d10", "1d20 - 2d6", "5d8 * 1d5".
        See https://en.wikipedia.org/wiki/Dice_notation for more information
        """
        accepted_math_operations = "+-/*)("

        dice_type = dice_type.lower()
        dice = map(
            dice_to_num,
            re.split(f"([{accepted_math_operations}])", dice_type.replace(" ", ""))
        )
        math_expr = re.sub(f"[^0-9{accepted_math_operations}]", "", "".join(map(str, dice)))

        #TODO: stop being stupid lmao
        await ctx.reply(eval(math_expr))


async def setup(bot: breadcord.Bot):
    await bot.add_cog(Yummy("yummy_toasts"))
