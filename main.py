import discord
from discord.ext import commands
import logging
import json

from BD import create_connection, execute_query, execute_read_query


from fireworks.client import Fireworks

token = "UR_TOKEN_HERE"



client = Fireworks(api_key="UR_API_KEY_HERE")


create_users_table = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    chat_history TEXT
);
"""

connection = create_connection("users.sqlite")
execute_query(connection, create_users_table)

handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user.name}")


@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel 
    prompt =f"""
        Your task is to analyze the given nickname and respond with the following points:

        Language or origin (if recognizable).

        Possible meaning or associations.

        Theme (gaming, crypto, meme, real-life, etc.).

        Possible positive and negative associations.

        How well the nickname fits for:

        a gaming community,

        business/professional context,

        a creative project.

        Provide a short overall characterization of the nickname in 2–3 sentences.

        Nickname: {member.name}
    """

    response = client.chat.completions.create(
        model="accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new",
        messages=[{"role": "system", "content": "You are a system that analyzes user nicknames."},
                  {"role": "user", "content": prompt}]
    )

    if channel is not None:
        await channel.send(f"Welcome {member.mention} to the server!\n\nYour nickname analysis is: {response.choices[0].message.content}")




@bot.command()
async def chat(ctx):
    user_id = ctx.author.id
    raw_history = execute_read_query(connection, "SELECT chat_history FROM users WHERE user_id = ?", (user_id,))
    if raw_history and raw_history[0][0]:
        messages = json.loads(raw_history[0][0])
    else:
        messages = [{"role": "system", "content": "You are a friendly assistant."}]

    messages.append({"role": "user", "content": ctx.message.content})

    response = client.chat.completions.create(
        model="accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new",
        messages=messages
    )
    answer = response.choices[0].message.content
    messages.append({"role": "assistant", "content": answer})
    execute_query(
    connection,
    "INSERT INTO users (user_id, chat_history) VALUES (?, ?) "
    "ON CONFLICT(user_id) DO UPDATE SET chat_history = ?",
    (user_id, json.dumps(messages), json.dumps(messages))
    )

    await ctx.send(answer)


@bot.command()
async def market_analysis(ctx):
    API_KEY = os.getenv("COINMARKETCAP_API_KEY")
    symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC"]
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"


    params = {
        "symbol": ",".join(symbols),
        "convert": "USD",
    }

    headers = {
        "Accept": "application/json",
        "X-CMC_PRO_API_KEY": API_KEY,
    }
   

    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    crypto_info = {}


    for symbol in symbols:
        crypto_info[symbol] = {
            "price": data["data"][symbol]["quote"]["USD"]["price"],
            "last_updated": data["data"][symbol]["quote"]["USD"]["last_updated"],
        }


    prompt = (
        "You are a professional cryptocurrency market analyst. I will give you the latest prices for the main cryptocurrencies, "
        "and your task is to analyze the market situation, assess possible short-term and medium-term trends, and give your opinion "
        "on potential risks and opportunities for investors.\n\n"
        "Here are the latest market data:\n"
    )

    for symbol, info in crypto_info.items():
        prompt += f"{symbol}: price: {info["price"]}, last updated: {info["last_updated"]}\n"

    prompt += (
        "\nPlease provide:\n"
        "1. General market sentiment (bullish, bearish, or neutral).\n"
        "2. Key observations from current price levels and volatility.\n"
        "3. Short-term prediction (next 3–7 days) and possible catalysts.\n"
        "4. Medium-term outlook (next 1–2 months).\n"
        "5. Potential risks for investors right now.\n"
        "6. Opportunities for profit if any.\n"
        "Give your answer in a structured format."
    )

    response = client.chat.completions.create(
        model="accounts/sentientfoundation/models/dobby-unhinged-llama-3-3-70b-new",
        messages=[{"role": "system", "content": "You are a professional cryptocurrency market analyst."},
                  {"role": "user", "content": prompt}]
    )
    answer = response.choices[0].message.content
    await ctx.send(answer)
    await ctx.send("‼️‼️Please note that the information provided in Dobby may be incomplete. This is not financial advice, but merely one example of how this model can be used.‼️‼️")



    
bot.run(token, log_handler=handler, log_level=logging.DEBUG)

