#Imports
import discord, json, os
import sqlite3 as sql
import numpy as np
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

#Track if we're in doc build mode or run mode.
try:
    SPHINX = os.environ['SPHINX']
except KeyError:
    SPHINX = None

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
if SPHINX == "sphinx":
    creds = ""
else:
    creds = service_account.Credentials.from_service_account_info(json.load(open("service.json")))
service = build("sheets","v4",credentials=creds)
sheet = service.spreadsheets()

#Sheet layout
statlayoutdict = {
    'name':"'Character Sheet'!C2",
    'race':"'Character Sheet'!C3",
    'class':"'Character Sheet'!C4",
    'level':"'Character Sheet'!C5",
    'height':"'Character Sheet'!C7",
    'weight':"'Character Sheet'!C8",
    'gender':"'Character Sheet'!C9",
    'image_url':"'Character Sheet'!D11",
    'image':"'Character Sheet'!B12",
    'bio':"'Character Sheet'!B29",
    'str':"'Character Sheet'!F3",
    'con':"'Character Sheet'!G3",
    'dex':"'Character Sheet'!H3",
    'int':"'Character Sheet'!I3",
    'cha':"'Character Sheet'!I4",
    'hpmax':"'Character Sheet'!H5",
    'manamax':"'Character Sheet'!H6",
    'evasion':"'Character Sheet'!H7",
    'speed':"'Character Sheet'!H8",
    'dr':"'Character Sheet'!H9",
    'teamlogo_url':"'Character Sheet'!J5",
    'teamlogo':"'Character Sheet'!I6",
    'head':"'Character Sheet'!Q3",
    'face':"'Character Sheet'!Q4",
    'neck':"'Character Sheet'!Q5",
    'shoulder1':"'Character Sheet'!Q6",
    'shoulder2':"'Character Sheet'!Q7",
    'upperarm1':"'Character Sheet'!Q8",
    'upperarm2':"'Character Sheet'!Q9",
    'lowerarm1':"'Character Sheet'!Q10",
    'lowerarm2':"'Character Sheet'!Q11",
    'hand1':"'Character Sheet'!Q12",
    'hand2':"'Character Sheet'!Q13",
    'ring1':"'Character Sheet'!Q14",
    'ring2':"'Character Sheet'!Q15",
    'ring3':"'Character Sheet'!Q16",
    'ring4':"'Character Sheet'!Q17",
    'ring5':"'Character Sheet'!Q18",
    'ring6':"'Character Sheet'!Q19",
    'ring7':"'Character Sheet'!Q20",
    'ring8':"'Character Sheet'!Q21",
    'ring9':"'Character Sheet'!Q22",
    'ring10':"'Character Sheet'!Q23",
    'torso':"'Character Sheet'!Q24",
    'waist':"'Character Sheet'!Q25",
    'upperleg1':"'Character Sheet'!Q26",
    'upperleg2':"'Character Sheet'!Q27",
    'knee1':"'Character Sheet'!Q28",
    'knee2':"'Character Sheet'!Q29",
    'lowerleg1':"'Character Sheet'!Q30",
    'lowerleg2':"'Character Sheet'!Q31",
    'foot1':"'Character Sheet'!Q32",
    'foot2':"'Character Sheet'!Q33",
    'skillnames':"'Character Sheet'!F13:F26,Skills and Inventory!B4:B",
    'skilldescs':"'Character Sheet'!H13:H26,Skills and Inventory!D4:D",
    'skillranks':"'Character Sheet'!N13:N26,Skills and Inventory!J4:J",
    'itemnames':"'Character Sheet'!J30:J40,Skills and Inventory!N4:N",
    'itemdescs':"'Character Sheet'!K30:K40,Skills and Inventory!O4:O",
    'itemweigh':"'Character Sheet'!N30:N40,Skills and Inventory!T4:T"
}

#sub-functions
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
    #Strip excess whitespace and quotes
    string = [x.strip().replace("'","").replace('"',"") for x in string]
    if string == ['']: string = []
    return string

def retrievename(token):
    try:
        name = sheet.values().get(spreadsheetId=token,range="Character Sheet!C2").execute().get("values",[])[0][0]
    except IndexError:
        name = "NAME_NOT_FOUND"
    return name

def assocformat(gAssoc,allowed=["all"]):
    gAssocnew = []
    for x in gAssoc:
        if x in allowed:
            gAssocnew.append(x)
        else:
            x = strtolist(x)[0]
            gAssocnew.append(int(x))
    return gAssocnew
