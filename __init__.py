import ast
import base64
import math
import operator
import random
import re
import string
import warnings
from collections.abc import Callable
from typing import Any, Iterable

import discord
import uwuify
from discord.ext import commands

import breadcord


def dice_to_num(dice_roll: str) -> int | None:
    if not (match := re.match(r"(?P<multiplier>\d*)d(?P<roll_max>\d+)", dice_roll, re.IGNORECASE | re.ASCII)):
        return None
    roll_max = int(match["roll_max"])
    multiplier = int(match["multiplier"] or 1)
    return sum(random.randint(1, roll_max) for _ in range(multiplier))


def eval_math(expression: str) -> Any:
    # Based on https://stackoverflow.com/a/9558001

    def limited_pow(a: float, b: float) -> float:
        if any(abs(n) > 10**4 for n in (a, b)):
            raise ValueError("Too large for exponentiation.")
        return operator.pow(a, b)

    operators: dict[type[ast.AST], Any] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.USub: operator.neg,
        ast.Mod: operator.mod,

        ast.Pow: limited_pow,
        ast.BitXor: limited_pow,  # ^
    }
    functions: dict[str, Callable[..., Any]] = {
        "max": max,
        "min": min,
        "abs": abs,
        "round": round,
        "ceil": math.ceil,
        "floor": math.floor,
        "sqrt": math.sqrt,
        "log": math.log,          "log10": math.log10, "log2": math.log2,
        "sin": math.sin,          "cos": math.cos,     "tan": math.tan,
        "asin": math.asin,        "acos": math.acos,   "atan": math.atan,   "atan2": math.atan2,
        "degrees": math.degrees, "radians": math.radians,
    }

    def eval_(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            return operators[type(node.op)](eval_(node.left), eval_(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return operators[type(node.op)](eval_(node.operand))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if not isinstance(node.func.ctx, ast.Load):
                raise SyntaxError("Only function calls are allowed")
            if (name := node.func.id) in functions:
                return functions[name](*map(eval_, node.args))
            raise NameError(f"Function {name!r} is not defined")
        raise TypeError(f"Unsupported AST node: {node.__class__.__name__}")

    return eval_(ast.parse(expression, mode="eval").body)


class Yummy(breadcord.module.ModuleCog):

    @commands.hybrid_command(
        edscription="Roll a die with a min and max value",
        aliases=["roll"],
    )
    async def dice(self, ctx: commands.Context, value: int = 6, max_value: int | None = None) -> None:
        if max_value is None:
            value, max_value = 1, value
        await ctx.reply(f"Rolled a {random.randint(value, max_value)}! 🎲")

    @commands.command(description="Evaluates a math expression")
    async def calc(self, ctx: commands.Context, *, user_input: str) -> None:
        """Evaluates a math expression."""
        try:
            out = eval_math(user_input)
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
                # In case converting the number to a string fails due to its size
                if re.match(r"^Exceeds the limit \(\d+\) for integer string conversion", error.args[0]):
                    await ctx.reply("Output too large, could not send.")
                    return
                raise

    @commands.hybrid_command(description="Flips a coin")
    async def coinflip(self, ctx: commands.Context) -> None:
        await ctx.reply(random.choice(("Heads", "Tails")))

    @commands.hybrid_command(descriptions="Generates a fake IP address")
    async def ip(self, ctx: commands.Context) -> None:
        await ctx.reply(".".join(str(random.randint(0, 255)) for _ in range(4)))

    @commands.hybrid_command(description="Generates a fake discord token")
    async def token(self, ctx: commands.Context) -> None:
        # Taken from https://github.com/Fripe070/FripeBot/blob/4d99df8a01bdacf970c552b3812e221a9a3070a8/cogs/fun.py#L261
        # I stole that code from somewhere else, but I can't remember where from
        def random_string(length=0, key=string.ascii_letters + string.digits + "-_"):
            return "".join(random.choice(key) for _ in range(length))

        if random.random() < 0.15:
            await ctx.reply(f"mfa.{random_string(math.floor(random.random() * (68 - 20)) + 20)}")
            return

        token_id = random_string(18, "0123456789").encode("ascii")
        encoded_id = base64.b64encode(bytes(token_id)).decode("utf-8")
        timestamp = random_string(math.floor(random.random() * (7 - 6) + 6))
        hmac = random_string(27)
        await ctx.reply(f"{encoded_id}.{timestamp}.{hmac}")

    @commands.hybrid_group(name="text", description="Various text modification commands")
    async def string_formatting_group(self, ctx: commands.Context) -> None:
        await ctx.send_help(ctx.command)

    @string_formatting_group.command(description="VaRiEs ThE cApItAlIsAtIoN oF iNpUt TeXt")
    async def varied(self, ctx: commands.Context, *, text: str) -> None:
        new_string = ""
        i = random.randint(0, 1)
        for char in text:
            if char.upper() == char and char.lower() == char:
                new_string += char
                continue
            i += 1
            new_string += char.upper() if i % 2 == 0 else char.lower()
        await ctx.reply(new_string)

    @string_formatting_group.command(
        description="Scrambles the order of characters in the input text",
        aliases=["shuffle"]
    )
    async def scramble(self, ctx: commands.Context, *, text: str) -> None:
        await ctx.reply("".join(random.sample(text, k=len(text))))

    @string_formatting_group.command(
        description="Scrambles the order of words in the input text",
        aliases=["scramblewords", "shuffle_words", "shufflewords"]
    )
    async def scramble_words(self, ctx: commands.Context, *, text: str) -> None:
        words = text.split(" ")
        await ctx.reply(" ".join(random.sample(words, k=len(words))))

    @string_formatting_group.command(
        description="Reverses the order of characters in the input text",
        aliases=["invert"]
    )
    async def reverse(self, ctx: commands.Context, *, text: str) -> None:
        await ctx.reply(text[::-1])

    @string_formatting_group.command(
        description="Reverses the order of words in the input text",
        aliases=["reversewords", "invert_words", "invertwords"]
    )
    async def reverse_words(self, ctx: commands.Context, *, text: str) -> None:
        await ctx.reply(" ".join(text.split(" ")[::-1]))

    @string_formatting_group.command(
        description="Uwuifies the input text",
        aliases=["owoify", "uwu", "owo"]
    )
    async def uwuify(self, ctx: commands.Context, *, text: str) -> None:
        await ctx.reply(uwuify.uwu(
            text,
            flags=uwuify.YU | uwuify.STUTTER | uwuify.SMILEY
        ))


async def setup(bot: breadcord.Bot, module: breadcord.module.Module) -> None:
    await bot.add_cog(Yummy(module.id))
