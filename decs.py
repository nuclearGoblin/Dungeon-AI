#Imports
import discord, json, os, re
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
botmail = os.getenv("BOTMAIL")

#regex stuff. taking everything as .lower().
#This section is really just reference because I'm terrible at reading regex
numbers = "\d+"
words = r"[a-z]\w?" #I will only interpret things as a name if they start with a letter.
numorword = "("+numbers+")|("+words+")"

#misc variables
bugreporttext = "Please submit a [bug report on our GitHub](https://github.com/nuclear-goblin/Dungeon-AI/issues)"

#Sheet layout
statlayoutdict = {
    'name':"Character Sheet!C2",
    'race':"Character Sheet!C3",
    'class':"Character Sheet!C4",
    'level':"Character Sheet!C5",
    'height':"Character Sheet!C7",
    'weight':"Character Sheet!C8",
    'gender':"Character Sheet!C9",
    'image_url':"Character Sheet!D11",
    'image':"Character Sheet!B12",
    'biography':"Character Sheet!B29",
    'strength':"Character Sheet!F3",
    'constitution':"Character Sheet!G3",
    'dexterity':"Character Sheet!H3",
    'intelligence':"Character Sheet!I3",
    'charisma':"Character Sheet!J3",
    'stats':"Character Sheet!F3:J3",
    'hpmax':"Character Sheet!H5",
    'manamax':"Character Sheet!H6",
    'evasion':"Character Sheet!H7",
    'speed':"Character Sheet!H8",
    'dr':"Character Sheet!H9",
    'teamlogo_url':"Character Sheet!J5",
    'teamlogo':"Character Sheet!I6",
    'head':"Character Sheet!Q3",
    'face':"Character Sheet!Q4",
    'neck':"Character Sheet!Q5",
    'shoulder1':"Character Sheet!Q6",
    'shoulder2':"Character Sheet!Q7",
    'upperarm1':"Character Sheet!Q8",
    'upperarm2':"Character Sheet!Q9",
    'lowerarm1':"Character Sheet!Q10",
    'lowerarm2':"Character Sheet!Q11",
    'hand1':"Character Sheet!Q12",
    'hand2':"Character Sheet!Q13",
    'ring1':"Character Sheet!Q14",
    'ring2':"Character Sheet!Q15",
    'ring3':"Character Sheet!Q16",
    'ring4':"Character Sheet!Q17",
    'ring5':"Character Sheet!Q18",
    'ring6':"Character Sheet!Q19",
    'ring7':"Character Sheet!Q20",
    'ring8':"Character Sheet!Q21",
    'ring9':"Character Sheet!Q22",
    'ring10':"Character Sheet!Q23",
    'torso':"Character Sheet!Q24",
    'waist':"Character Sheet!Q25",
    'upperleg1':"Character Sheet!Q26",
    'upperleg2':"Character Sheet!Q27",
    'knee1':"Character Sheet!Q28",
    'knee2':"Character Sheet!Q29",
    'lowerleg1':"Character Sheet!Q30",
    'lowerleg2':"Character Sheet!Q31",
    'foot1':"Character Sheet!Q32",
    'foot2':"Character Sheet!Q33",
    'skillnames':"Skills and Inventory!B4:B",
    'skilldescs':"Skills and Inventory!D4:D",
    'skillranks':"Skills and Inventory!J4:J",
    'skilltrack':"Skills and Inventory!K4:K", #!K4:K #this one is not searched.
    'skillexp':"Skills and Inventory!L", #!L4:L #this one is not searched.
    'skillinfo':"Skills and Inventory!B4:L",
    'itemnames':"Skills and Inventory!P4:P",
    'itemdescs':"Skills and Inventory!Q4:Q",
    'itemweigh':"Skills and Inventory!V4:V",
    'experience':"Character Sheet!Q40",
    'unspent':"Character Sheet!Q39",
    'currenthp':"Character Sheet!Q38"
}

skillTrackTable = {
        'S': [0,1,2, 3 ,4, 5, 6, 7, 8,  9,  10, 11, 12, 13,14, 15, 16, 17, 18, 19, 20],
        'A': [0,1,5, 9 ,13,17,21,25,29, 33, 37, 41, 45, 49,53, 57, 61, 65, 69, 73, 77],
        'B': [0,1,9, 17,25,33,41,49,57, 65, 73, 81, 89, 97,105,113,121,129,137,145,153],
        'C': [0,1,13,25,37,49,61,73,85, 97, 109,121,133,145,157,169,181,193,205,217,229],
        'D': [0,1,16,31,46,61,76,91,106,121,136,151,166,181,196,211,226,241,256,271,286]
        }

def hp(con: int): #Calculate max HP
    return con*(10+(con-1)/2)

#sub-functions
def readonlytest(token):
    try:
        testinput = {"values":[["a"]]}
        testloc = "Character Sheet!S41"
        sheet.values().update(spreadsheetId=token,range=testloc,valueInputOption="USER_ENTERED",body=testinput).execute()
        gotback = sheet.values().get(spreadsheetId=token,range=testloc).execute().get("values",[])
        if gotback != testinput["values"]:
            raise ValueError("Tried to input "+str(testinput)+"but got back "+str(gotback)+".")
        return False
    except HttpError:
        return True
    
def strtolist(string):
    if type(string) != str: #fallback case for non-string passed in.
        return string
    #Chop off the start/end brackets
    if(string[0] == "[" and string[-1] == "]"): 
        string = string[1:-1]
    string = string.split(",") #Separate entries
    #Strip excess whitespace and quotes
    string = [x.strip().replace("'","").replace('"',"") for x in string]

#Check for sublists
    i = 0
    substring = []
    substring_open = -1
    toPop = []
    while i < len(string): #while
        if string[i][0] == "[":
            substring_open = i
            substring = [string[i][1:]]
        elif string[i][-1] == "]":
            substring.append(string[i][:-1])
            toPop.append(i)
            string[substring_open] = substring
            substring_open = -1
        else:
            if substring_open >= 0:
                substring.append(string)
                toPop.append(i)
        i += 1

    for x in sorted(toPop,reverse=True):
        string.pop(x)

    if string == ['']: 
        string = []

    return string

def retrievevalue(location,token): #This function is for SINGULAR values ONLY!
    try:
        value = sheet.values().get(spreadsheetId=token,range=location).execute().get("values",[])[0][0]
    except IndexError:
        value = "VALUE_NOT_FOUND"
    return value

def assocformat(gAssoc,allowed=["all"]):
    gAssocnew = []
    for x in gAssoc:
        if x in allowed:
            gAssocnew.append(x)
        else:
            x = strtolist(x)[0]
            gAssocnew.append(int(x))
    return gAssocnew

def check_alias(name):
    list = []
    for key in statlayoutdict.keys():
        if name.lower() in key:
            list.append(key)
    if len(list) == 1:
        return list[0]
    if len(list) == 0:
        return ("NAME_NOT_FOUND",name)
    return (list,name)

def retrieveMcToken(guildID: str,userID,guilds,users):
    #First, check if current guild has an assigned main character for the user.
    gRow = guilds.loc[guilds['userID'] == userID]
    if gRow.empty:
        return None
    mcIDs = strtolist(gRow.iloc[0]["mainCharIDs"])
    gIDs = strtolist(gRow.iloc[0]["guildIDs"])
    try:
        gloc = gIDs.index(guildID)
    except ValueError: #The player doesn't have anything in this guild at all
        return None
    if mcIDs[gloc] is not None: #There is a default character for the current guild
        return mcIDs[gloc]
    #There is no default character for the current guild specifically
    uRow = users.loc[users['userID'] == userID]
    associated = []
    for i,x in enumerate(uRow["guildAssociations"]):
        if guildID in x: #If the sheet is associated with the guild,
            associated.append(i) #Append its ID to the list
            if len(associated) > 1: return None #If there are too many, give up
    if len(associated) == 1: #If we found a valid character,
        return uRow["charIDs"].values[associated[0]]#Return the character ID found
    for i,x in enumerate(uRow["guildAssociations"]): #No specific associations,
        if "all" in x and associated == []: #So check for "all"
            associated.append(i)
            if len(associated) > 1: return None #Again, too many; give up.
    if len(associated) == 1:
        return uRow["charIDs"].values[associated[0]] #Return the character ID found
    #We never found anything. too bad.
    return None
        
def getSkillInfo(skillname,token):
    #for reference
    #value    = sheet.values().get(spreadsheetId=token,range=location).execute().get("values",[])[0][0]
    tosearch = sheet.values().get(spreadsheetId=token,range=statlayoutdict["skillnames"]).execute().get("values",[])
    column = statlayoutdict["skillranks"]
    row = str(int(statlayoutdict["skillnames"].split("!")[1].split(":")[0][1:])+tosearch.index([skillname]))
    if [skillname] not in tosearch: #If it's not in either, assume that the player hasn't trained the skill.
        return 0
    #tosearch = ["".join(entry.lower().split()) ]
    sheetname,column = column.split("!")
    column = column.split(":")[0][0]

    return int(retrievevalue(sheetname+"!"+column+row,token)),row

def giveExp(skill: int,rank: int,token,skillname: str):
    message = "You gained one experience point in **"+skillname+"**"

    #Get the current value
    loc_exp = statlayoutdict['skillexp']+str(skill)
    currentexp = int(retrievevalue(loc_exp,token))+1

    #Check for rank-up
    maxExp = skillTrackTable[retrievevalue(statlayoutdict['skilltrack']+str(skill),token)][rank]
    if currentexp >= maxExp:
        #Rankups don't happen until combat is over, so the player will have to handle that themselves.
        message += ", allowing you to progress to the next rank!"
    else:
        message += "."
    
    #Update the exp value
    sheet.values().update(spreadsheetId=token,range=loc_exp,
                                body={'values':[[str(currentexp)]],'range':loc_exp, 'majorDimension':'ROWS'},
            valueInputOption = 'USER_ENTERED').execute()
    return message

def signed(intval,mode): #microfunction for handling an if/else I have to do like a hundred times
    if mode == "+":
        return intval
    return 0-intval #Currently only modes are +/- so this is fine.

def unspent_check(self):
    #Enable addition if points are newly unspent
    if self.unspent > 0:
        for child in self.children:
            if (type(child) is discord.ui.Button) and child.label[0] == "+":
                child.disabled = False
    #Disable addition if there are no points to spend
    else:
        for child in self.children:
            if (type(child) is discord.ui.Button) and child.label[0] == "+":
                child.disabled = True
    #Disable "Save" if nothing is changed
    if self.str_up == self.con_up == self.dex_up == self.int_up == self.cha_up == 0:
        for child in self.children:
            if (type(child) is discord.ui.Button) and (child.label == "Save" or child.label[0] == "-"):
                child.disabled = True
    #Enable "Save" if something has changed
    else:
        for child in self.children:
            if (type(child) is discord.ui.Button) and child.label == "Save":
                child.disabled = False
                child.emoji = None

def update_embed(self):
    editembed = self.embed.to_dict()
    editembed['description'] = "Points remaining: "+str(self.unspent)
    return discord.Embed.from_dict(editembed)

def hp_color(frac: float):
    if frac == 0:
        return 0x000000
    else:
        return discord.Color.from_rgb(int(255*(1-frac)),int(255*frac),0)

def getHpFromEmbed(view: discord.ui.View,interaction): #Microfunction to reduce copying
    loc = view.clickedby.index(interaction.user)
    embed = view.embeds[loc]
    current = int(embed.footer.text.split("/")[0].split(" ")[1])
    return loc,embed,current

def getHpForEmbed(view: discord.ui.View,token: str):
    retrieve = [statlayoutdict["dr"],
                statlayoutdict["currenthp"],
                statlayoutdict["hpmax"],
                statlayoutdict["name"]]
    dr,current,maxhp,name=sheet.values().batchGet(spreadsheetId=token,ranges=retrieve).execute()['valueRanges']
            #These are auto-calculated so they should be auto-filled
    dr = int(dr['values'][0][0])
    maxhp = int(maxhp['values'][0][0])
    try:
        name = name['values'][0][0]
    except KeyError: #if name is blank, use placeholder
        name = "Untitled Character"
    try: 
        current = int(current['values'][0][0])
    except KeyError: #if current hp is missing, assume it's full.
        #Yes, this behavior differs from the levelup function
        #Because in this instance if I assume they have no HP they just insta-die.
        current = maxhp
    return dr,current,maxhp,name

## The roll function! this is a big one
def mod_parser(modifier,goal,autoexp,interaction,guilds,users):
    #Set up things to return
    rollname = "Rolling `1d20"
    mod = 0
    skillname = None
    skillrow = None
    rank = None
    token = None
    button_view = None
    #Parse the modifier and search for the token
    if modifier != "":
        modifier = modifier.lower() #prevent case-sensitivity
        modifier = "".join(modifier.split()) #strip extra whitespace  
        rollname += "+"+modifier
        if not re.search(r"\b[+-]?((\d+)|([a-z]\w*))?([+-]((\d+)|([a-z]\w*)))*$",modifier):
            return 1 
        mode = [sym for sym in modifier if sym in "+-"]
        if modifier[0] not in "+-": #If it's not picked up here,
            mode.insert(0,"+")      #It's a positive leading value.
        if re.search("[+-]",modifier):
            modifier=re.split("[+-]",modifier)
        if type(modifier) is not list:
            modifier = [modifier] #if modifier is a single value, make it a one-item list
        token = retrieveMcToken(str(interaction.guild_id),interaction.user.id,guilds,users)
        for i,entry in enumerate(modifier):
            if entry.isdigit(): #If the value is a number,
                mod += signed(int(entry),mode[i])
            else:
                modalias = check_alias(entry)
                if type(modalias) is str:
                    toadd = d.retrievevalue(statlayoutdict[modalias],token)
                elif token is None:
                    return 2
                else:
                    toadd,skillrow = getSkillInfo(entry,token)
                    rank = toadd
                    skillname = entry
                if toadd == "HTTP_ERROR":
                    mod = "HTTP_ERROR"
                    break #Stop calculating it and tell them to do it themselves
                else: 
                    mod += signed(int(toadd),mode[i])
    #Generate a d20 roll
    result = np.random.randint(1,20)
    #Generate a string representing the dice rolled
    resultstring = str(result)
    rollname = rollname+"`! Result: ["+resultstring+"]"
    if mod>0:
        rollname = rollname+" + "+str(mod)
    elif mod<0:
        rollname = rollname+" - "+str(abs(mod))
    result += mod
    rollname = rollname+" = **"+str(result)
    if goal is not None:
        rollname += "** vs **"+str(goal)    
        if mod == "HTTP_ERROR":
            rollname += ". There was an error connecting to Google Sheets when retrieving modifiers. "
            rollname += "Please manually calculate your roll. "
        else:
            if result >= goal: 
                rollname += " (Success!)"
            else: 
                rollname += " (Failure...)"
    rollname = rollname+"**." #end bold

    try: #If a skill was rolled, we will look at experience.
        if not readonlytest(token):
            if autoexp:
                expmsg = giveExp(skillrow,rank,token,skillname) #assigns message while processing
                rollname += " "+expmsg
            else:
                button_view = expButton()
                button_view.token = token
                button_view.skillrow = skillrow
                button_view.skillrank = rank
                button_view.skillname = skillname
                button_view.message = rollname+" "
                button_view.parentInter = interaction
        else:
            rollname += " Don't forget to update your skill experience." 
    except UnboundLocalError: #skillname is undefined, so we weren't rolling a skill
        pass
            
    #Give all the values back now
    return mod,rollname,skillname,skillrow,rank,token,result,button_view

def reconstruct_response_lists(embed,responding,passing):
    txt = ""
    for user in responding:
        txt += user.display_name+", "
    embed.set_field_at(0,name="Responding",value=txt[-1])
    txt = ""
    for user in passing:
        txt += user.display_name+", "
    embed.set_field_at(1,name="Passing",value=txt[-1],inline=False)

#####################
# Classes ###########
#####################

class expButton(discord.ui.View):
    def __init__(self):
        super().__init__()

        self.token = None
        self.skillrow = None
        self.skillrank = None
        self.skillname = None
        self.private = True
        self.message = ""
        self.parentInter = None

    @discord.ui.button(label="Gain Skill EXP",style=discord.ButtonStyle.success)
    async def click(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.message += giveExp(self.skillrow,self.skillrank,self.token,self.skillname)
        button.disabled = True
        button.label = "EXP Gained"
        button.emoji = "✔️"
        await self.parentInter.edit_original_response(content=self.message,view=self)#,ephemeral=self.private)
        #self.stop()
        await interaction.response.defer()

class statAllocationButtons(discord.ui.View):
    def __init__(self):
        super().__init__()
        #To be passed in
        self.token = None
        self.strength = 0
        self.con = 0
        self.dex = 0
        self.intellect = 0
        self.cha = 0
        self.unspent = 0
        self.parentInter = None
        self.embed = None
        self.currenthp = 0
        #To be manipulated here only
        self.str_up = 0
        self.con_up = 0
        self.dex_up = 0
        self.int_up = 0
        self.cha_up = 0

    # Buttons for adding stats --------------------------------------------------------
    @discord.ui.button(label="+ STR",style=discord.ButtonStyle.primary,custom_id="strUp")
    async def click_strUp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.strength += 1
        self.unspent -= 1
        if self.unspent <= 0:
            button.disabled = True
            self.private = False
        self.str_up += 1
        for child in self.children:
            if (type(child) is discord.ui.Button) and child.label in ["- STR","Save"]:
                child.disabled = False
        unspent_check(self)
        #Update the embed accordingly
        self.embed.set_field_at(0,name="Strength",value=self.strength)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="+ CON",style=discord.ButtonStyle.primary,custom_id="conUp")
    async def click_conUp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.con += 1
        self.unspent -= 1
        if self.unspent <= 0:
            button.disabled = True
        self.con_up += 1
        for child in self.children:
            if (type(child) is discord.ui.Button) and child.label in ["- CON","Save"]:
                child.disabled = False
        unspent_check(self)
        #Update the embed accordingly
        self.embed.set_field_at(1,name="Constitution",value=self.con)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="+ DEX",style=discord.ButtonStyle.primary,custom_id="dexUp")
    async def click_dexUp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.dex += 1
        self.unspent -= 1
        if self.unspent <= 0:
            button.disabled = True
        self.dex_up += 1
        for child in self.children:
            if (type(child) is discord.ui.Button) and child.label in ["- DEX","Save"]:
                child.disabled = False
        unspent_check(self)
        #Update the embed accordingly
        self.embed.set_field_at(2,name="Dexterity",value=self.dex)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="+ INT",style=discord.ButtonStyle.primary,custom_id="intUp")
    async def click_intUp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.intellect += 1
        self.unspent -= 1
        if self.unspent <= 0:
            button.disabled = True
        self.int_up += 1
        for child in self.children:
            if (type(child) is discord.ui.Button) and child.label in ["- INT","Save"]:
                child.disabled = False
        unspent_check(self)
        #Update the embed accordingly
        self.embed.set_field_at(3,name="Intelligence",value=self.intellect)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="+ CHA",style=discord.ButtonStyle.primary,custom_id="chaUp")
    async def click_chaUp(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cha += 1
        self.unspent -= 1
        if self.unspent <= 0:
            button.disabled = True
        self.cha_up += 1
        for child in self.children:
            if (type(child) is discord.ui.Button) and child.label in ["- CHA","Save"]:
                child.disabled = False
        unspent_check(self)
        #Update the embed accordingly
        self.embed.set_field_at(4,name="Charisma",value=self.cha)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    #Buttons for subtracting stats ----------------------------------------------------
    @discord.ui.button(label="- STR",style=discord.ButtonStyle.danger,disabled=True,custom_id="strDn")
    async def click_strDn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.strength -= 1
        self.unspent += 1
        self.str_up -= 1
        if self.str_up <= 0:
            button.disabled = True
        unspent_check(self)
        self.embed.set_field_at(0,name="Strength",value=self.strength)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()


    @discord.ui.button(label="- CON",style=discord.ButtonStyle.danger,disabled=True,custom_id="conDn")
    async def click_conDn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.con -= 1
        self.unspent += 1
        self.con_up -= 1
        if self.con_up <= 0:
            button.disabled = True
        unspent_check(self)
        self.embed.set_field_at(1,name="Constitution",value=self.con)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="- DEX",style=discord.ButtonStyle.danger,disabled=True,custom_id="dexDn")
    async def click_dexDn(self, interaction: discord.Interaction, button:discord.ui.Button):
        self.dex -= 1
        self.unspent += 1
        self.dex_up -= 1
        if self.dex_up <= 0:
            button.disabled = True
        unspent_check(self)
        self.embed.set_field_at(2,name="Dexterity",value=self.dex)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="- INT",style=discord.ButtonStyle.danger,disabled=True,custom_id="intDn")
    async def click_intDn(self, interaction: discord.Interaction, button:discord.ui.Button):
        self.intellect -= 1
        self.unspent += 1
        self.int_up -= 1
        if self.int_up <= 0:
            button.disabled = True
        unspent_check(self)
        self.embed.set_field_at(3,name="Intelligence",value=self.intellect)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="- CHA",style=discord.ButtonStyle.danger,disabled=True,custom_id="chaDn")
    async def click_chaDn(self,interaction: discord.Interaction, button:discord.ui.Button):
        self.cha -= 1
        self.unspent += 1
        self.cha_up -= 1
        if self.cha_up <= 0:
            button.disabled = True
        unspent_check(self)
        self.embed.set_field_at(4,name="Charisma",value=self.cha)
        self.embed = update_embed(self)
        #And send it
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="Save",style=discord.ButtonStyle.success,disabled=True,custom_id="save")
    async def click(self, interaction: discord.Interaction, button:discord.ui.Button):
        #Lock in changes
        oldmaxhp = hp(self.con - self.con_up)
        newmaxhp = hp(self.con)
        self.currenthp += newmaxhp - oldmaxhp
        self.str_up = 0
        self.con_up = 0
        self.dex_up = 0
        self.int_up = 0
        self.cha_up = 0
        unspent_check(self)
        button.emoji = "✔️"
        #update the sheet
        requests = {
                'value_input_option': 'USER_ENTERED',
                'data': [
                    {'range':statlayoutdict["stats"],
                                    'values':[[str(self.strength),str(self.con),str(self.dex),str(self.intellect),str(self.cha)]]},
                    {'range':statlayoutdict["unspent"],
                                    'values':[[self.unspent]]},
                    {'range':statlayoutdict["currenthp"],
                                    'values':[[self.currenthp]]}
                ]
                }
        sheet.values().batchUpdate(spreadsheetId=self.token,body=requests).execute()
        #And send the update to discord
        await self.parentInter.edit_original_response(view=self,embed=self.embed)
        await interaction.response.defer()

class endEncounter(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.pips = 0
        self.message = ""
        self.parentInter = None
        self.guilds = None
        self.users = None
        #Track who clicked the button to prevent silly exp farming 
        self.clickedby = []

    @discord.ui.button(label="Gain pips",style=discord.ButtonStyle.success)
    async def click(self, interaction: discord.Interaction, button:discord.ui.Button):
        if interaction.user in self.clickedby: #If the same person clicks it twice,
            await interaction.response.defer() #Ignore them they're silly
        else: #Otherwise,
            self.clickedby.append(interaction.user) #Note that they clicked it
            desc = ""
            for user in self.clickedby:
                desc += "<@"+str(user.id)+">, "
            embed = discord.Embed(title="Pips claimed by:",description=desc[:-2])
            await self.parentInter.edit_original_response(content=self.message,view=self,embed=embed)
            token = retrieveMcToken(str(interaction.guild_id),interaction.user.id,self.guilds,self.users)
            exp = int(retrievevalue(statlayoutdict["experience"],token))+self.pips
            sheet.values().update(spreadsheetId=token,range=statlayoutdict["experience"],
                                body={'values':[[exp]],'range':statlayoutdict["experience"], 'majorDimension':'ROWS'},
                                valueInputOption = 'USER_ENTERED').execute()
            await interaction.response.defer()

class takeDamage(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.damage = 0
        self.message = ""
        self.parentInter = None
        self.guilds = None
        self.users = None
        self.embed = None
        self.bypass = False
        #Allow undo by re-pressing.
        self.clickedby = []
        self.embeds = []

    @discord.ui.button(label="Take damage",style=discord.ButtonStyle.danger)
    async def click(self, interaction: discord.Interaction, button:discord.ui.Button):
        #Get character sheet
        token = retrieveMcToken(str(interaction.guild_id),interaction.user.id,self.guilds,self.users)
        if interaction.user in self.clickedby:
            #Figure out relevant parameters
            loc,embed,current=getHpFromEmbed(self,interaction)
            current += int(embed.fields[0].value) #Add back the taken damage.
            #Remove user from damage taken list
            self.embeds.pop(loc)
            self.clickedby.pop(loc)
            #Apply changes to character sheet
            #Update original message
            await self.parentInter.edit_original_response(content=self.message,view=self,embeds=self.embeds)
        else:
            #Get values
            dr,current,maxhp,name = getHpForEmbed(self,token)
            if not self.bypass:
                self.damage -= dr
                self.damage = max(self.damage,0)
            current -= self.damage
            current = max(0,current) #hp below 0 is game over -- dead is dead!

            self.embeds.append(discord.Embed(title=name,description=interaction.user.mention,color=hp_color(current/maxhp)))
            self.clickedby.append(interaction.user)

            self.embeds[-1].add_field(name="Taken:",value=self.damage)
            self.embeds[-1].set_footer(text="Remaining: "+str(current)+"/"+str(maxhp))

            #Respond
            await self.parentInter.edit_original_response(content=self.message,view=self,embeds=self.embeds)
        #Update sheet and respond to button
        sheet.values().update(spreadsheetId=token,range=statlayoutdict["currenthp"],valueInputOption="USER_ENTERED",body={'values':[[current]]}).execute()
        await interaction.response.defer()

class takeHealing(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.damage = 0
        self.message = ""
        self.parentInter = None
        self.guilds = None
        self.users = None
        self.embed = None
        self.overheal = False
        #Allow undo by re-pressing.
        self.clickedby = []
        self.embeds = []
        

    @discord.ui.button(label="Receive healing",style=discord.ButtonStyle.success)
    async def click(self, interaction: discord.Interaction, button:discord.ui.Button):
        #Get character sheet
        token = retrieveMcToken(str(interaction.guild_id),interaction.user.id,self.guilds,self.users)
        if interaction.user in self.clickedby:
            #Figure out relevant parameters
            loc,embed,current=getHpFromEmbed(self,interaction)
            current -= int(embed.fields[0].value) #Subtract the healing back out. sorry!
            if not overheal:
                current = max(current,0)
            #Remove user from damage taken list
            self.embeds.pop(loc)
            self.clickedby.pop(loc)
            #Apply changes to character sheet
            #Update original message
            await self.parentInter.edit_original_response(content=self.message,view=self,embeds=self.embeds)
        else:
            #Get values
            _,current,maxhp,name = getHpForEmbed(self,token)
            current += self.damage
            current = min(current,maxhp) #overhealing bad
            self.embeds.append(discord.Embed(title=name,description=interaction.user.mention,color=hp_color(current/maxhp)))
            self.clickedby.append(interaction.user)

            self.embeds[-1].add_field(name="Received:",value=self.damage)
            self.embeds[-1].set_footer(text="Remaining: "+str(current)+"/"+str(maxhp))

            #Respond
            await self.parentInter.edit_original_response(content=self.message,view=self,embeds=self.embeds)
        #Update sheet and respond to button
        sheet.values().update(spreadsheetId=token,range=statlayoutdict["currenthp"],valueInputOption="USER_ENTERED",body={'values':[[current]]}).execute()
        await interaction.response.defer()


class requestRoll(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.mod = ""
        self.guilds = None
        self.users = None
        self.message = ""
        self.goal = 0
        self.auto = True
        self.parentInter = None
        #Don't let the same user reroll repeatedly.
        self.clickedby = []
        self.embed = discord.Embed(title="Rolled by:")
        self.success = []

    @discord.ui.button(label="Roll",style=discord.ButtonStyle.primary)
    async def click(self, interaction: discord.Interaction, button:discord.ui.Button):
        if interaction.user in self.clickedby:
            pass #You don't get to roll twice nerd!
        else:
            self.clickedby.append(interaction.user)
            
            parsed_mod = mod_parser(self.mod,self.goal,self.auto,interaction,self.guilds,self.users)
            if parsed_mod == 1:
                await parentInter.edit_original_response(content=
                    "`modifier` argument format not recognized. "
                    + "Please follow the format `skillname+statname+X`,"
                    + "ex `coolness+charisma-13`.")
                await interaction.response.defer()
                return 1
            elif parsed_mod == 2:
                result = "No character selected!"
                self.success.append(False)
            else:
                mod,_,skillname,skillrow,rank,token,result,_ = parsed_mod
                if result >= self.goal:
                    self.success.append(True)
                else:
                    self.success.append(False)
                result = str(result) + " ("+str(result-mod)+"+"+str(mod)+")"
            if self.success[-1]:
                result = "✔️ "+result
            else:
                result = "❌ "+result
            self.embed.add_field(name=interaction.user.name,value=result,inline=False)
            #Shuffle around to change color
            self.embed = self.embed.to_dict()
            self.embed['color'] = int(hp_color(self.success.count(True)/len(self.success)))
            self.embed = discord.Embed.from_dict(self.embed)
            #and reply
            await self.parentInter.edit_original_response(content=self.message,view=self,embed=self.embed)
        await interaction.response.defer()
