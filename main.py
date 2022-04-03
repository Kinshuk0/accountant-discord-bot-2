import asyncio
import re
import uuid
import sys
import logging
import discord
import psycopg2
from discord.utils import get
import os
from dotenv import load_dotenv
from datetime import datetime
from discord.ext import commands
from sqlalchemy import BigInteger, create_engine, Column, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT")

engine = create_engine("postgresql://doadmin:kiqsBNTds0PV7JgE@db-postgresql-nyc3-22503-do-user-10924482-0.b.db.ondigitalocean.com:25060/defaultdb", echo=False)
Base = declarative_base()


class Wallet(Base):
    __tablename__ = "whitelisted_wallets"

    uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user = Column("user", String)
    server_id = Column("server_id", BigInteger)
    address = Column("address", String)


Base.metadata.create_all(bind=engine)
# Session = sessionmaker(bind=engine)
# session = Session()

EMPTY = "\u200b"
CHANNEL_NAME = "💰│submit-address"
CHANNEL_NAME_1 = "💰│submit-address"
ROLE_NAME = "Wallet Recorded"
pattern = re.compile("^0x[a-fA-F0-9]{40}$")

bot = commands.Bot("!")


def init_session():
    Session = sessionmaker(bind=engine)
    session = Session()

    return session


def get_logger() -> logging.Logger:
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    file_handler = logging.FileHandler(f"{ENVIRONMENT}.log")
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    log.addHandler(stdout_handler)

    return log


log = get_logger()


@bot.event
async def on_ready():
    log.info(f"🚀 {bot.user} is now online in {ENVIRONMENT}!")


@bot.event
async def on_guild_join(guild):
    created_channel = await guild.create_text_channel(CHANNEL_NAME)
    created_role = await guild.create_role(name=ROLE_NAME)
    description = """I am your wallet accountant bot. Send your ethereum wallet addresses in this channel to get them whitelisted!

Admins can use the `!wallets` command to retrieve the wallets data in a well-formatted csv.

**PS - DO NOT RENAME/REMOVE THIS CHANNEL.**"""
    embed = discord.Embed(
        title=f"Greetings {guild.name} 👋",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )
    embed.set_thumbnail(
        url="https://www.pngitem.com/pimgs/m/124-1245793_ethereum-eth-icon-ethereum-png-transparent-png.png"
    )
    if created_channel and created_channel.permissions_for(guild.me).send_messages:
        await created_channel.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True, ban_members=True)
async def wallets(ctx: commands.Context):
    log.info("🚀 Wallets command called!")

    server_id = int(ctx.guild.id)

    session = init_session()

    try:
        wallets = session.query(Wallet).filter(Wallet.server_id==server_id)

        with open(f"wallets.csv", "w") as f:
            f.write(f"Discord Handle, Whitelisted address\n")

            for wallet in wallets:
                f.write(f"{wallet.user}, {wallet.address}\n")

        file = discord.File("wallets.csv")

        embed = discord.Embed(
            title=f"Whitelisted Addresses",
            color=discord.Color.from_rgb(255, 192, 203),
            timestamp=datetime.utcnow(),
            description="Find your users wallet addresses in `wallets.csv`!"
        )

        await ctx.send(file=file, embed=embed)

    except Exception as e:
        log.info(e)
        await ctx.reply(
                "The bot is currently offline for maintenance 🚧, Please try again in a while."
            )
    finally:
        session.close()


@bot.event
async def on_message(message):
    log.info("🚀 On message event called!")

    server_id = int(message.guild.id)
    
    if str(message.channel.name) == CHANNEL_NAME_1:
        if message.author != bot.user:
            wl_address = str(message.content)

            if wl_address == "!wallets":
                await bot.process_commands(message)
                return

            if not pattern.match(wl_address):
                embed = discord.Embed(
                    title="Invalid Format",
                    color=discord.Color.greyple(),
                    description=EMPTY,
                    timestamp=datetime.utcnow()
                )
                msg = await message.channel.send(embed=embed)

                await asyncio.sleep(4)
                await message.delete()
                await msg.delete()

                await bot.process_commands(message)
                return

            ctx_author = str(message.author)
            
            session = init_session()

            try:
                if session.query(
                    session.query(Wallet).filter(Wallet.user == ctx_author, Wallet.server_id == server_id).exists()
                ).scalar():
                    wallet = session.query(Wallet).filter(Wallet.user == ctx_author, Wallet.server_id == server_id)[0]
                    wallet.address = wl_address
                    session.commit()
                    embed = discord.Embed(
                        title="Whitelisted Address",
                        color=discord.Color.from_rgb(255, 192, 203),
                        description=f"Gotchu {message.author.mention}! Your wallet address for mints has been updated (`{wl_address}`)",
                        timestamp=datetime.utcnow()
                    )
                    # getrolebyname
                    role = get(member.server.roles, name=ROLE_NAME)
                    member = message.author
                    # addrole
                    await member.add_roles(role)
                    msg = await message.channel.send(embed=embed)
                else:
                    wallet = Wallet(
                        user=ctx_author,
                        server_id=server_id,
                        address=wl_address
                    )
                    session.add(wallet)
                    session.commit()
                    embed = discord.Embed(
                        title="Whitelisted Address",
                        color=discord.Color.from_rgb(255, 192, 203),
                        description=f"Gotchu {message.author.mention}! Your wallet address for mints has been recorded (`{wl_address}`)",
                        timestamp=datetime.utcnow()
                    )
                    msg = await message.channel.send(embed=embed)
                
                await asyncio.sleep(4)
                await message.delete()
                await msg.delete()
                
            except Exception as e:
                log.info(e)
                await message.channel.send(
                    "The bot is currently offline for maintenance 🚧, Please try again in a while."
                )
            
            finally:
                session.close()

    await bot.process_commands(message)


if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
