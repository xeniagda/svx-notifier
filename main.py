from typing import Optional

import discord
import asyncio
import svx
import aiohttp

import logging

PING_CHANNEL_ID = 984834553782886480
SVX_ROLE = 984735416341114910
PING_ROLE = 984735416341114910

BOT_LOG = logging.getLogger("bot")

class SvxNotifierBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot_ch = None

    async def on_ready(self):
        BOT_LOG.info("Bot ready!")
        self.bot_ch = await self.fetch_channel(PING_CHANNEL_ID)

    async def on_message(self, msg: discord.Message):
        author = msg.author
        if not isinstance(author, discord.Member):
            return

        guild = author.guild
        ping_role = guild.get_role(PING_ROLE)

        if ping_role is None:
            BOT_LOG.critical("Ping role not found!")
            return

        # add role
        if msg.content == "!bing":
            # BOT_LOG.
            if not ping_role in author.roles:
                BOT_LOG.info(f"Giving {author.name} ping role")
                await author.add_roles(ping_role, reason="!bing")
                await msg.reply(f"Du har nu fått rollen **@{ping_role.name}**")
            else:
                BOT_LOG.info(f"{author.name} already has ping role")
                await msg.reply(f"Du har redan rollen **@{ping_role.name}**. Använd !bong för att bli av med den!")

        # remove role
        if msg.content == "!bong":
            if ping_role in author.roles:
                BOT_LOG.info(f"Removing {author.name} ping role")
                await author.remove_roles(ping_role, reason="!bong")
                await msg.reply(f"Du har nu inte längre rollen **@{ping_role.name}**.")
            else:
                await msg.reply(f"Du har ej rollen **@{ping_role.name}**. Använd !bing för att få den!")


    async def svx_notification(self, node: svx.Node, time_since_last: Optional[float]):
        if self.bot_ch is None:
            BOT_LOG.error("Trying to send notification before connection!")
            return

        msg = f"Nod **{node.name}** i **{node.location}** gick igång på talk group **{node.talk_group}** <@&{SVX_ROLE}>!!! "
        if time_since_last is not None:
            h = int(time_since_last / 3600)
            m = int((time_since_last % 3600) / 60 + 0.5)
            msg += f"Denna station har inte sagt någonting på {h}:{m:02} minuter"

        await self.bot_ch.send(msg)
        BOT_LOG.info(f"Sent {msg!r}")


def get_token() -> str:
    with open("token.secret") as token_file:
        return token_file.read().strip()


if __name__ == "__main__":
    MAIN_LOG = logging.getLogger("main")

    async def start():
        bot = SvxNotifierBot()
        MAIN_LOG.info("Bot logging in")
        await bot.login(get_token())
        MAIN_LOG.info("Setting up SVXNotifier...")

        async with aiohttp.ClientSession() as sess:
            svx_notifier = svx.SVXNotifier(sess)
            svx_notifier.add_callback(bot.svx_notification)

            asyncio.create_task(svx_notifier.poll_periodically())

            MAIN_LOG.info("Bot connecting")
            await bot.connect()

    asyncio.run(start())
