#Imports
import os, discord
from commands import * #load our commands without need for ref
from dotenv import load_dotenv

#Setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
print(type(os.getenv('TEST_SERVER_ID')),type(TOKEN))
testguild = discord.Object(id=os.getenv('TEST_SERVER_ID'))

#Verify connection in server output
@client.event
async def on_ready():
    tree.clear_commands(guild=testguild)
    await tree.sync()
    print(f'{client.user} has connected to Discord!')
#Run 
client.run(TOKEN)