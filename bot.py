#Imports
import os, discord
import pandas as pd
import sqlite3 as sql
from commands import * #load our commands without need for ref
from dotenv import load_dotenv

#Setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
print(type(os.getenv('TEST_SERVER_ID')),type(TOKEN))
testguild = discord.Object(id=os.getenv('TEST_SERVER_ID'))

users = sql.connect()
if userdb_present:
    #check the columns
    pass #because there's no code here yet
else:
    #create the missing database
    df = pd.DataFrame()
    connection=sql.connect('dungeon')
    #df.to_sql(name='users',con=connection) #well first we want it to have something in it.
#do again for chars, settings

#Verify connection in server output
@client.event
async def on_ready():
    tree.clear_commands(guild=testguild)
    await tree.sync()
    print(f'{client.user} has connected to Discord!')
#Run 
client.run(TOKEN)