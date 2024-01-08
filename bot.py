#Imports
import os, discord
from dotenv import load_dotenv

#Setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
intents = discord.Intents.none()
print(intents)
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

#Commands -- move these to another file maybe?
@tree.command(
    name="ls",
    description="list available commands",
    guild=discord.Object(id=1193956362611331162)
)
async def ls(interaction: discord.Interaction):
    await interaction.response.send_message("ls -- gives this help menu.")

#Verify connection in server output
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=1193956362611331162))
    print(f'{client.user} has connected to Discord!')
#Run 
client.run(TOKEN)