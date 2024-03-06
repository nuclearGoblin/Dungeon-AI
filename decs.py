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
guildCols = ["userID","guildIDs","mainCharIDs"]
connection = sql.connect("characters.db")
