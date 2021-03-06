import asyncio
import io
import os
import logging
from dataclasses import dataclass

import discord
from discord.ext.commands import Bot, Group, Command

from utils import run_in_executor
from bot.session import Chart
from bot.session_manager import SessionManager
from chart import convert_svg_png
from bot.discrd.render.chart import ChartRenderer
from bot.discrd.render.text_message import TextMessageRenderer
from users import get_users as get_os_users


users = get_os_users()
session_manager = SessionManager(users)

chart_renderer = ChartRenderer()
message_renderer = TextMessageRenderer()


@dataclass
class SubcommandNotFound:
    subcommand: str


@run_in_executor
def create_chart_file(svg_text):
    png_bytes = convert_svg_png(svg_text)

    return discord.File(io.BytesIO(png_bytes), filename="chart.png")


async def format_message(notification, session=None):
    if isinstance(notification, Chart):
        chart_scores = notification.chart_scores
        svg_text = await chart_renderer.render(session, scores=chart_scores)
        return await create_chart_file(svg_text)

    else:
        return await message_renderer.render(session, notification)


async def gago(ctx, subcommand):
    message = await format_message(SubcommandNotFound(subcommand))
    await ctx.reply(message)


async def push_notifications(channel_id, exercise):
    session = session_manager.get_session(channel_id)

    async for notification in session.start(exercise):
        try:
            channel = bot.get_channel(channel_id)
            message = await format_message(notification, session)

            if isinstance(message, discord.File):
                await channel.send(file=message)
            else:
                await channel.send(message)
        except discord.DiscordException as e:
            logging.exception(e)


async def start(ctx, exercise=None):
    channel_id = ctx.channel.id
    asyncio.create_task(push_notifications(channel_id, exercise))


async def stop(ctx):
    channel_id = ctx.channel.id
    session = session_manager.get_session(channel_id)

    notification = await session.stop()
    message = await format_message(notification, session)

    await ctx.reply(message)


async def periodic(ctx):
    channel_id = ctx.channel.id
    session = session_manager.get_session(channel_id)

    notification = session.toggle_periodic()
    message = await format_message(notification, session)

    await ctx.reply(message)


async def set_user(ctx, user=None):
    member = ctx.message.author
    channel_id = ctx.channel.id
    session = session_manager.get_session(channel_id)

    notification = session.register(user, member)
    message = await format_message(notification, session)

    await ctx.reply(message)


async def show_users(ctx):
    async with ctx.typing():
        members = ctx.guild.members
        channel_id = ctx.channel.id
        session = session_manager.get_session(channel_id)

        notification = session.get_users_status(members)
        message = await format_message(notification, session)

        await ctx.reply(message)


async def chart(ctx, exercise=None):
    channel_id = ctx.channel.id
    session = session_manager.get_session(channel_id)

    async for notification in session.chart(exercise):
        message = await format_message(notification, session)

        if isinstance(message, discord.File):
            await ctx.reply(file=message)
        else:
            await ctx.reply(message)


intents = discord.Intents.default()
intents.members = True
bot = Bot(intents=intents, command_prefix=("$", "!", "/"))

group = Group(gago, invoke_without_command=True)


def is_admin(ctx):
    channel = ctx.channel
    permissions = channel.permissions_for(ctx.author)
    return permissions.administrator


group.add_command(Command(start, checks=[is_admin]))
group.add_command(Command(stop, checks=[is_admin]))
group.add_command(Command(periodic, checks=[is_admin]))
group.add_command(Command(set_user, name="user", aliases=("setuser",)))
group.add_command(Command(show_users, name="users"))
group.add_command(Command(chart, aliases=("scores", "leaderboard")))

bot.add_command(group)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    TOKEN = os.environ["DISCORD_BOT_TOKEN"]

    bot.run(TOKEN)
