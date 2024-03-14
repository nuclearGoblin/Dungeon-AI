#Imports
import discord, json
import sqlite3 as sql
import numpy as np
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#Load up environment envs
load_dotenv()

#Discord stuff
client = discord.Client(intents=discord.Intents.none())
tree = discord.app_commands.CommandTree(client)

#sql stuff
userCols = ["userID","charIDs","guildAssociations","readonly"]
guildCols = ["userID","guildIDs","mainCharIDs"]
charCols = ["charID","accessLevel"]
connection = sql.connect("characters.db")
types = {'userID': np.dtype('int64')}

#Google stuff
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = service_account.Credentials.from_service_account_info(json.load(open("service.json")))
service = build("sheets","v4",credentials=creds)
sheet = service.spreadsheets()

#Microfunctions
def readonlytest(token):
    try:
        testinput = {"values":[["a"]]}; testloc = "Character Sheet!S41"
        sheet.values().update(spreadsheetId=token,range=testloc,valueInputOption="USER_ENTERED",body=testinput).execute()
        gotback = sheet.values().get(spreadsheetId=token,range=testloc).execute().get("values",[])
        if gotback != testinput["values"]:
            raise ValueError("Tried to input "+str(testinput)+"but got back "+str(gotback)+".")
        return False
    except HttpError:
        print("read only.")
        return True
    
def strtolist(string):
    if type(string) != str: #fallback case for non-string passed in.
        return string
    #Chop off the start/end brackets
    if(string[0] == "[" and string[-1] == "]"): string = string[1:-1]
    string = string.split(",") #Separate entries
    #Strip excess whitespace and single-quotes
    string = [x.strip().replace("'","") for x in string]
    if string == ['']: string = []
    return string