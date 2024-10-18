import discord
import os
import aiohttp
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Datos de tu bot de Discord desde variables de entorno
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# Datos de tu bot de Telegram desde variables de entorno
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_IDS = set()
TELEGRAM_OFFSET = None

# Inicializa el bot de Discord
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Sesión HTTP asíncrona
async def send_to_telegram(message):
    if not TELEGRAM_CHAT_IDS:
        print("No hay usuarios registrados para recibir mensajes en Telegram.")
        return

    async with aiohttp.ClientSession() as session:
        for chat_id in TELEGRAM_CHAT_IDS:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            try:
                async with session.post(url, data=data) as response:
                    if response.status != 200:
                        print(f"Error al enviar mensaje a Telegram (chat_id {chat_id}): {await response.text()}")
            except Exception as e:
                print(f"Excepción al enviar mensaje a Telegram: {str(e)}")

# Función para obtener los chat_id de Telegram
async def get_telegram_chat_id():
    global TELEGRAM_OFFSET
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    params = {}
    if TELEGRAM_OFFSET:
        params['offset'] = TELEGRAM_OFFSET

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if "result" in data and len(data["result"]) > 0:
                        for result in data["result"]:
                            update_id = result["update_id"]
                            message = result.get("message")
                            
                            if message and "text" in message:
                                chat_id = message["chat"]["id"]
                                text = message["text"]
                                
                                if text == "/alpha":
                                    TELEGRAM_CHAT_IDS.add(chat_id)
                                    print(f"Chat ID registrado: {chat_id}")
                                elif text == "/stop":
                                    TELEGRAM_CHAT_IDS.discard(chat_id)
                                    print(f"Chat ID eliminado: {chat_id}")

                            TELEGRAM_OFFSET = update_id + 1
                else:
                    print(f"Error al obtener chat_ids: {response.status}")
        except Exception as e:
            print(f"Excepción al obtener chat_ids de Telegram: {str(e)}")

@bot.event
async def on_ready():
    print(f'Bot {bot.user} conectado')
    bot.loop.create_task(monitor_telegram_async())

async def monitor_telegram_async():
    while True:
        await get_telegram_chat_id()
        await asyncio.sleep(5)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if DISCORD_CHANNEL_ID and message.channel.id != DISCORD_CHANNEL_ID:
        return
    if message.embeds:
        for embed in message.embeds:
            embed_fields = []
            if embed.title:
                embed_fields.append(f"*{embed.title}*")
            if embed.description:
                embed_fields.append(embed.description)
            for field in embed.fields:
                embed_fields.append(f"*{field.name}*: {field.value}")
            telegram_message = "\n".join(embed_fields).replace('**', '*')
            await send_to_telegram(telegram_message)
    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)
