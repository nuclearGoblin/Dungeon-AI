#Imports
import os, discord, json
import pandas as pd
from decs import *
from google.oauth2 import service_account
from googleapiclient.discovery import build

#Secrets
TOKEN = os.getenv('DISCORD_TOKEN')
testguild = discord.Object(id=os.getenv('TEST_SERVER_ID'))

#Google setup
SAMPLE_SPREADSHEET_ID = "1sRKjgEWwBr9cS_9KEvog6Y6_Ud3E0wI3URK56seRcmc"
SAMPLE_RANGE_NAME = "Character Sheet!B2:B5"

#Call the Google API to make sure it's working.
if SPHINX == "sphinx":
    pass
else:
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,range=SAMPLE_RANGE_NAME).execute()
    values = result.get("values",[])
    if not values:
        raise ValueError("No data found in spreadsheet "+SAMPLE_SPREADSHEET_ID)
    else:
        print("DEBUG =================")
        for row in values: print(row)

#Check the database on spin-up -- don't want things to blip on if they're broken.
try: #Check if the tables needed exist
    users = pd.read_sql("SELECT * FROM users",connection,dtype=types)
except pd.io.sql.DatabaseError: #If they don't,
    users = pd.DataFrame(columns=userCols)
    #user id [1], list of guild ids [n], list of default character identifiers [n], list of character ids [m], list of guilds with access to character [awk m]
    users.to_sql(name='users',con=connection) #Create them.
    print("`users` table was not present -- created!")
if False: #Not actually sure we need chars db
    try: #Check if the tables needed exist
        chars = pd.read_sql("SELECT * FROM chars",connection)
    except pd.io.sql.DatabaseError: #If they don't,
        chars = pd.DataFrame(columns=charCols)
        chars.to_sql(name='chars',con=connection)
        print("`chars` table was not present -- created!")
try: #Check if the tables needed exist
    guilds = pd.read_sql("SELECT * FROM guilds",connection,dtype=types)
except pd.io.sql.DatabaseError: #If they don't,
    guilds = pd.DataFrame(columns=guildCols)
    guilds.to_sql(name='guilds',con=connection)
    print("`guilds` table was not present -- created!")

#Now we can get commands imported
from commands import * #load our commands without need for ref

#Verify connection in server output
@client.event
async def on_ready():
    tree.clear_commands(guild=testguild)
    await tree.sync()
    print(f'{client.user} has connected to Discord!')
#Run 
if SPHINX == "sphinx":
    print("Finished running in sphinx mode. Exiting!")
    exit(0)
client.run(TOKEN)