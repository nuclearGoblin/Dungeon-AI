#Imports
import discord, re
import numpy as np
import pandas as pd
from decs import *

#Setup
users = pd.read_sql("SELECT * FROM users",connection)
chars = pd.read_sql("SELECT * FROM chars",connection)
guilds = pd.read_sql("SELECT * FROM guilds",connection)

#List of commands. Important!
@tree.command(
    name="help",
    description="Lists available commands",
)
async def help(interaction: discord.Interaction):
    message = """**help** - Prints this help menu.
**roll** - Rolls a die, default 1d20, see command for options.
**link** - Links a character sheet to your user for this server."""
    await interaction.response.send_message(message,ephemeral=True)

#Basic die rolls.
@tree.command(
    name="roll",
    description="Default: rolls 1d20. Rolls a number of dice with minimum, maximum, and modifier."
)
@discord.app_commands.describe(
    dice="String representing the dice rolled, in format `XdY+Z`, `XdY-Z`, or `XdY`. (Default: 1d20)",
    goal="Value to meet or exceed.",
    private="Hide roll from other users. (Default: False)"
    #mod="Modifier for the die roll.",
    #high="Maximum value of the dice rolled (for XdY, this is Y).",
    #low="Minimum value of the dice rolled (for normal dice, this is 1).",
    #numdice="How many dice to roll (for XdY, this is X)."
)
async def roll(interaction: discord.Interaction, dice: str="", goal: int=None, private: bool=False):#, mod: int=0, high: int=20, low: int=1, numdice: int=1): #don't really need all these anymore.
    mod = 0; high = 20; numdice = 1; #Defaults -- comment out if you reinclude the extra args.
    #Take a human-looking dice input
    if dice != "":
        if mod != 0 or high != 20 or numdice != 1: #If other defaults were changed, abort.
            await interaction.response.send_message("Please do not combine the `dice` argument with other numeric arguments.",ephemeral=True)
            return 1
        if not re.search(r"\b\d+d\d+([+-]\d+)*$",dice):
            await interaction.response.send_message("`dice` argument format not recognized. Please follow the format `XdY+Z`, `XdY-Z`, or `XdY`. Example `2d8+12`.",ephemeral=True)
            return 1
        #String processing
        numdice,dice = dice.split("d")
        #Get modifier
        if re.search("[+]",dice): 
            high,mod=dice.split("+")
        elif re.search("[-]",dice): 
            high,mod=dice.split("-")
            mod = "-"+mod
        else: #there was no modifier.
            high=dice
        #Convert everything to integer
        high = int(high); mod = int(mod); numdice = int(numdice)
    rollname = "Rolling "
    #Check if we're rolling normal dice.
    #if low == 1: 
    rollname = rollname+str(numdice)+"d"+str(high)
    #else:
    #    rollname = rollname+str(low)+" to "+str(high)
    #    if numdice > 1: rollname = rollname+" a total of "+str(numdice)+" times"
    #Check the modifier
    if mod>0:
        rollname = rollname+" + "+str(mod)
    elif mod<0:
        rollname = rollname+" - "+str(abs(mod))
    #Generate a result
    result = np.random.randint(1,high,numdice)
    #Generate a string representing the dice rolled
    resultstring = ""
    for x in result:
        resultstring = resultstring+str(x)+", "
    resultstring = resultstring[:-2]
    rollname = rollname+"! Result: ["+resultstring+"]"
    if mod>0:
        rollname = rollname+" + "+str(mod)
    elif mod<0:
        rollname = rollname+" - "+str(abs(mod))
    result = sum(result)+mod
    if mod != 0 or numdice > 1:
        rollname = rollname+" = **"+str(result)
    if goal != None:
        if result >= goal:
            rollname = rollname+"** vs **"+str(goal)+" (Success!)"
        else:
            rollname = rollname+"** vs **"+str(goal)+" (Failure...)"
    rollname = rollname+"**."
    await interaction.response.send_message(rollname,ephemeral=private)

#Character sheet linking
@tree.command(
    name="link",
    description="Links a character sheet to your user on this server. If already linked, modifies link settings."
)
@discord.app_commands.describe(
    url="The URL of your character sheet.",
    default="Set the character sheet as your default character sheet for the current guild. (Default: True)",
    allguilds="Access this character sheet from all Discord servers you are in. (Default: False).",
)
async def link(interaction: discord.Interaction, url: str="", default: bool=True, allguilds: bool=False):
    global users,chars,guilds
    if "." in url: #This is a full URL, so we need to strip it
        token = url.split("https://") #Remove this first if it's present, since we're splitting on / this would cause issues.
        token = url.split("/") #Now split along slashes.
        token = token[3] #Take the third entry
    elif "/" in url: #I don't know how to interpret this. You left out .com but included slashes so I don't know where to start.
        await interaction.response.send_message("Unable to interpret provided url. Please either provide the full URL of your document or only the token.",ephemeral=True)
        return
    else: token = url
    #Now that we have a token, see if the user is in the table.
    if interaction.user.id not in users["userID"]:
        gRow = pd.DataFrame([interaction.user.id,[],[]],columns=guildCols) #fill placeholders in a moment
        uRow = pd.DataFrame([interaction.user.id,[],[[]]],columns=userCols)
        message = "Updated "
    else:
        gRow = guilds.loc[guilds['userID'] == interaction.user.id]
        uRow = users.loc[users['userID'] == interaction.user.id]
        message = "Linked "
    #See if the character is already in the table
    if token not in uRow[1]: uRow[1].append(token)
    pos = uRow[1].index(token) #Store where in the row it is.
    guildID = interaction.guild.id
    #See if the token is already associated with this guild and allguild and default statuses are not changing.
    if (guildID in uRow[2][pos] and not allguilds) or (uRow[2][pos] == "all" and allguilds):
        if (token in gRow[2][gRow[1].index(guildID)]) != default:
            await interaction.response.send_message("This character is already linked as described. Nothing to do!")
            return
    #See if we need to add the current guild to the list of guilds.
    if guildID not in gRow[1]: gRow[1].append(guildID)
    #If this character is to be the default for this guild, we should associate them.
    if default: gRow[2][gRow[1].index(guildID)] = token
    #Set up guild association for character.
    if allguilds: uRow[2][pos] = "all"
    elif guildID not in uRow[2][pos]:
        if uRow[2][pos] == "all": uRow[2][pos] = [guildID]
        else: uRow[2][pos].append(guildID)
    #Save the data!
    users = pd.concat([users,uRow])
    users.to_sql(name='users',con=connection)
    guilds = pd.concat([guilds,gRow])
    guilds.to_sql(name='guilds',con=connection)
    #Construct a nice pretty message.
    name = "NAME_PLACEHOLDER"
    message.append(name+" with ID "+token+" to be associated with ")
    if allguilds: message.append("all guilds")
    else: message.append("this guild")
    if default: message.append(" and function as the default for this guild")
    message.append(".")
    await interaction.response.send_message(message,ephemeral=True)

#async def unlink()
#Let someone unlink data.
    
#force refresh
#Force refresh character data (should be done automatically but may not always be good)
    
#view
#view links

#So this should use one database with two tables:
#1. Table containing user/guild/character sheet data.
# - User ID, Guild ID, Character ID, Character Name, "default" status.
#2. Table containing character data.
# - Character ID, all relevant status, integrated with google sheets.

#Other commands to write:
#unlink (if no ID provided, unlink all data in current guild. If "all guilds" option provided, delete all user data.)
#mergecharacters (merge all characters associated with User ID into )
#show (show all linked character sheets, with names + IDs. Users can only see their own data unless they are server owners, in which case they can see all data for the guild.)
#rename (rename a character sheet. if no arg, update the name based on the sheet.)
#skillroll (roll the associated skill+modifiers, this is the main function we want)
#requestroll (be able to request players click a button and roll a thing.)
#configure (bot settings per server, maybe uses a third table, things like who can view sheets and request rolls.)
