import ast
import base64
import math
import operator
import random
import re
import string
import warnings
from typing import Any, Iterable

import discord
import uwuify
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
        ast.USub: operator.neg,
        ast.Mod: operator.mod,

        ast.Pow: limited_pow,
        ast.BitXor: limited_pow,  # ^
    }

    def eval_(node):
        if isinstance(node, ast.Num):  # <number>
            return node.n
        elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
            # noinspection PyTypeChecker
            return operators[type(node.op)](eval_(node.left), eval_(node.right))
        elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
            # noinspection PyTypeChecker
            return operators[type(node.op)](eval_(node.operand))
        else:
            raise TypeError(node)

    return eval_(ast.parse(expression, mode='eval').body)


class ANSIEscape:
    def __init__(self, *code: Any, prefix: str = "\033[", suffix: str = "m"):
        self.code = map(str, code)
        self._prefix = prefix
        self._suffix = suffix

    def __str__(self) -> str:
        return self._prefix + ";".join(self.code) + self._suffix

    def __len__(self) -> int:
        return len(str(self))


def strip_blank_codeblock(codeblock: str, /) -> str:
    codeblock = codeblock.strip()
    if not (codeblock.startswith("```") and codeblock.endswith("```")):
        return codeblock

    match = re.match(
        r"```(?:[a-z]+\n)?(?P<code>.+)```",
        codeblock,
        flags=re.DOTALL | re.IGNORECASE
    )
    if not match:
        return codeblock

    lines = match["code"].splitlines()

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def regex_match_codeblock(matches: Iterable[re.Match[str]], match_against: str) -> str:
    matches = tuple(matches)
    if not matches:
        return "No matches found."

    colours = [
        31,  # Red
        33,  # Yellow
        32,  # Green
        36,  # Cyan
        34,  # Blue
        35,  # Magenta
    ]

    start_indices = tuple(match.start() for match in matches)
    end_indices = tuple(match.end() for match in matches)

    output = ""
    current_match_count = 0
    for index, character in enumerate(match_against):
        if index in end_indices and index not in start_indices:
            output += str(ANSIEscape(0))  # Reset colour

        if index in start_indices:
            colour = colours[current_match_count % len(colours)]
            current_match_count += 1
            output += str(ANSIEscape(colour))

        output += character

    return f"```ansi\n{output}\n```"


class Yummy(breadcord.module.ModuleCog):
    @discord.app_commands.command()
    async def regex(self, interaction: discord.Interaction, *, regex: str, match_against: str, flags: str = ""):
        flags = [flag.upper() for flag in flags.replace(",", " ").split() if flag]
        try:
            flags = [getattr(re.RegexFlag, flag) for flag in flags]
            flag_bitfield = sum(flags)
        except AttributeError:
            await interaction.response.send_message(embed=discord.Embed(
                color=discord.Colour.red(),
                title="Error",
                description=(
                    "Invalid flag(s) provided. "
                    "For a list of valid flags, see <https://docs.python.org/3/library/re.html#flags>"
                )
            ))
            return

        match_against = strip_blank_codeblock(match_against)
        regex = strip_blank_codeblock(regex)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                regex = re.compile(regex, flags=flag_bitfield)
        except re.error as error:
            error_message = str(error)[0].title() + str(error)[1:]
            await interaction.response.send_message(embed=discord.Embed(
                color=discord.Colour.red(),
                title="Error",
                description=error_message
            ))
            return

        matches = tuple(regex.finditer(match_against))
        output_embed = discord.Embed(
            color=discord.Colour.green(),
            title="Results",
            description=(
                f"**Regex:**```\n{regex.pattern}```\n"
                + (f"**Flags:** {', '.join(f'`{flag.name}`' for flag in flags)}\n\n" if flags else "")
                + f"**Matches:**{regex_match_codeblock(matches, match_against)}"
            )
        ).set_footer(text=f"Total matches: {len(matches)}")
        await interaction.response.send_message(embed=output_embed)

    @commands.hybrid_command(description='Roll a die with a min and max value')
    async def dice(self, ctx: commands.Context, value: int = 6, max_value: int = None):
        if max_value is None:
            value, max_value = 1, value
        await ctx.reply(f"Rolled a {random.randint(value, max_value)}! 🎲")

    @commands.command(description="Evaluates a math expression")
    async def calc(self, ctx: commands.Context, *, user_input: str):
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
                # In vase converting the number to a string fails due to its size
                if re.match(r"^Exceeds the limit \(\d+\) for integer string conversion", error.args[0]):
                    await ctx.reply("Output too large, could not send.")
                    return
                raise

    @commands.hybrid_command(description="Flips a coin")
    async def coinflip(self, ctx: commands.Context):
        await ctx.reply(random.choice(("Heads", "Tails")))

    @commands.hybrid_command(descriptions="Generates a fake IP address")
    async def ip(self, ctx: commands.Context):
        await ctx.reply(".".join(str(random.randint(0, 255)) for _ in range(4)))

    @commands.hybrid_command(description="Generates a fake discord token")
    async def token(self, ctx: commands.Context):
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
    async def varied(self, ctx: commands.Context, *, text: str):
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
    async def scramble(self, ctx: commands.Context, *, text: str):
        await ctx.reply("".join(random.sample(text, k=len(text))))

    @string_formatting_group.command(
        description="Scrambles the order of words in the input text",
        aliases=["scramblewords", "shuffle_words", "shufflewords"]
    )
    async def scramble_words(self, ctx: commands.Context, *, text: str):
        words = text.split(" ")
        await ctx.reply(" ".join(random.sample(words, k=len(words))))

    @string_formatting_group.command(
        description="Reverses the order of characters in the input text",
        aliases=["invert"]
    )
    async def reverse(self, ctx: commands.Context, *, text: str):
        await ctx.reply(text[::-1])

    @string_formatting_group.command(
        description="Reverses the order of words in the input text",
        aliases=["reversewords", "invert_words", "invertwords"]
    )
    async def reverse_words(self, ctx: commands.Context, *, text: str):
        await ctx.reply(" ".join(text.split(" ")[::-1]))

    @string_formatting_group.command(
        description="Uwuifies the input text",
        aliases=["owoify", "uwu", "owo"]
    )
    async def uwuify(self, ctx: commands.Context, *, text: str):
        await ctx.reply(uwuify.uwu(
            text,
            flags=uwuify.YU | uwuify.STUTTER | uwuify.SMILEY
        ))


async def setup(bot: breadcord.Bot):
    await bot.add_cog(Yummy("yummy_toasts"))
