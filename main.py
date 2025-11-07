import discord
from discord import app_commands
from discord.ui import Select, View, Button
import os

# Token del bot (usar variable de entorno en producción)
TOKEN = os.getenv('DISCORD_TOKEN', 'MTQzNjI3OTQwMzA3OTI3NDU5Ng.GozFPG.ici1sNaqDYC5azmpZB08zkji2fhv5Ev-wPDZo4')
GUILD_ID = 1310024114312056832

# Contador de ofertas
offer_counter = 1
active_offers = {}

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f'Bot conectado como {client.user}')
    except Exception as e:
        print(f'Error: {e}')

# El código completo del bot irá aquí
# Ver el archivo completo en la documentación

client.run(TOKEN)
