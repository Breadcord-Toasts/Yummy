import random
import re
import ast
import operator
from typing import Any

import discord
from discord.ext import commands

import breadcord


def dice_to_num(dice_roll: str) -> int | str:
    if not (match := re.match(r"^(?P<multiplier>\d*)d(?P<roll_max>\d+)", dice_roll)):
        return dice_roll

    roll_max = int(match["roll_max"])
    multiplier = int(match["multiplier"] or 1)
    return sum(random.randint(1, roll_max) for _ in range(multiplier))


def eval_math(expression: str) -> Any:
    # Based on https://stackoverflow.com/a/9558001

    def limited_pow(a: float, b: float) -> float:
        if any(abs(n) > 10**4 for n in (a, b)):
            raise ValueError("Too large for exponentiation.")
        return operator.pow(a, b)

    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Pow: limited_pow,
        ast.USub: operator.neg,
        ast.Mod: operator.mod,
    }

    # noinspection PyTypeChecker
    # I'm sure it's finneee
    def eval_(node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return operators[type(node.op)](eval_(node.left), eval_(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return operators[type(node.op)](eval_(node.operand))
        else:
            raise TypeError(node)

    return eval_(ast.parse(expression, mode='eval').body)


class Yummy(breadcord.module.ModuleCog):
    @commands.hybrid_command(description='Roll a die with a min and max value')
    async def dice(self, ctx: commands.Context, value: int = 6, max_value: int = None):
        if max_value is None:
            value, max_value = 1, value
        await ctx.reply(f"Rolled a {random.randint(value, max_value)}! 🎲")

    @commands.hybrid_command(description="Evaluate a math expression with support for dice notation")
    async def calc(self, ctx: commands.Context, *, dice_type: str):
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

        try:
            out = eval_math(math_expr)
        except Exception as error:
            await ctx.reply(f"Could not evaluate.\n{discord.utils.escape_markdown(str(error))}")
            return
        else:
            discord_message_limit = 2000
            try:
                if len(out := str(out)) > discord_message_limit:
                    out = f"{out[:discord_message_limit - 3]}..."
                await ctx.reply(out)
            except ValueError as error:
                # In vase converting the number to a string fails due to its size
                if re.match(r"^Exceeds the limit \(\d+\) for integer string conversion", error.args[0]):
                    await ctx.reply("Output too large, could not send.")
                    return
                raise error

    @commands.hybrid_command(description="Flips a coin")
    async def coinflip(self, ctx: discord.Context):
        await ctx.reply(random.choice(("Heads", "Tails")))

    @commands.hybrid_command(descriptions="Generates a fake IP adress")
    async def ip(self, ctx: discord.Context):
        await ctx.reply(".".join(str(random.randint(0, 255)) for _ in range(4)))


async def setup(bot: breadcord.Bot):
    await bot.add_cog(Yummy("yummy_toasts"))
