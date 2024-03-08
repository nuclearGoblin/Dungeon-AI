#Imports
import os, discord
from dotenv import load_dotenv
import sqlite3 as sql

#Load up environment envs
load_dotenv()

#Discord stuff
client = discord.Client(intents=discord.Intents.none())
tree = discord.app_commands.CommandTree(client)

#sql stuff
userCols = ["userID","charIDs","guildAssociations"]
uTypes = {"userID":int,"charIDs":list,"guildAssociations":list}
guildCols = ["userID","guildIDs","mainCharIDs"]
gTypes = {"userID":int,"guildIDs":list,"mainCharIDs":list}
charCols = ["charID"]
cTypes = {"charID":int}
connection = sql.connect("characters.db")
