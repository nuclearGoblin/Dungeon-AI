#Imports
import discord, re
import numpy as np
import pandas as pd
from decs import *
import googleapiclient.errors

#Setup
users = pd.read_sql("SELECT "+", ".join(userCols)+" FROM users",connection)
#chars = pd.read_sql("SELECT "+", ".join(charCols)+" FROM chars",connection)
guilds = pd.read_sql("SELECT "+", ".join(guildCols)+" FROM guilds",connection)

#List of commands. Important!
@tree.command(
    name="help",
    description="Lists available commands",
)
async def help(interaction: discord.Interaction):
    message = """**help** - Prints this help menu.
**roll** - Rolls a die, default 1d20, see command for options.
**link** - Links a character sheet to your user for this server.
**view** - View the character sheets that you've linked to this server."""
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
    global users,guilds#,chars
    #Token interpretation
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
        gRow = pd.DataFrame([[interaction.user.id,[],[]]],columns=guildCols) #fill placeholders in a moment
        uRow = pd.DataFrame([[interaction.user.id,[],[[]],[]]],columns=userCols)
        message = "Linked "
        concat = True
    else:
        gRow = guilds.loc[guilds['userID'] == interaction.user.id]
        uRow = users.loc[users['userID'] == interaction.user.id]
        message = "Updated "
        concat = False
    if False: #commenting these out for now until char db set up -- which is maybe never!
        if token not in chars["charID"]: 
            cRow = [token] 
            #do stuff to generate the character in the database
        else: #go ahead and force update while we're here
            #update the character
            pass
    #See if the character is already in the table
    if token not in uRow.iloc[0]["charIDs"]: uRow.iloc[0]["charIDs"].append(token)
    pos = uRow.iloc[0]["charIDs"].index(token) #Store where in the row it is.
    guildID = interaction.guild.id
    #Test read the character sheet.
    try:
        name = sheet.values().get(spreadsheetId=token,range="Character Sheet!C2").execute().get("values",[])
    except googleapiclient.errors.HttpError:
        await interaction.response.send_message("Unable to reach character sheet. Please make sure that it is either public or shared with the bot, whose email is: `discord-test@dungeon-ai-416903.iam.gserviceaccount.com`",ephemeral=True)
        return
    if not name: name = "PLACEHOLDER_NAME"
    else: name = name[0][0]
    #Test write to the character sheet.
    readonly = readonlytest(token)
    #See if the token is already associated with this guild and allguild and default statuses are not changing, and that the readonly status wouldn't change.
    if ((guildID in uRow.iloc[0]["guildAssociations"][pos] and not allguilds) or (uRow.iloc[0]["guildAssociations"][pos] == "all" and allguilds)) and readonly == uRow.iloc[0]["readonly"][pos]:
        if (token in gRow.iloc[0]["mainCharIDs"][gRow.iloc[0]["guildIDs"].index(guildID)]) != default:
            await interaction.response.send_message("This character is already linked as described. Nothing to do!")
            return
    #Update read-only status now that it's been checked.
    roArray = uRow.iloc[0]["readonly"]
    try:
        roArray[pos] = readonly
    except IndexError: #Unless it's not in the list yet.
        roArray.append(readonly)
    uRow.at[0,"readonly"] = roArray
    #See if we need to add the current guild to the list of guilds.
    if guildID not in gRow.iloc[0]["guildIDs"]: 
        gRow.iloc[0]["guildIDs"].append(guildID)
    #If this character is to be the default for this guild, we should associate them.
    if default: 
        try: #Try reassigning if exists
            gRow.iloc[0]["mainCharIDs"][gRow.iloc[0]["guildIDs"].index(guildID)] = token
        except IndexError: #If it doesn't, create it.
            gRow.iloc[0]["mainCharIDs"].append(token)
            if len(gRow.iloc[0]["mainCharIDs"]) < gRow.iloc[0]["guildIDs"].index(guildID): #If we still don't have that many indices,
                raise ValueError("Your character database is corrupted. Please copy down the information you can with `/view char:all`, clear your database with `/unlink char:all`, and recreate it. Please also [submit a bug report on our GitHub](https://github.com/nuclearGoblin/Dungeon-AI).")
    #Set up guild association for character.
    if allguilds: 
        assocs = uRow.iloc[0]["guildAssociations"]
        assocs[pos] = "all"
        uRow.at[0,"guildAssociations"] = assocs
    elif guildID not in uRow.iloc[0][2][pos]:
        if uRow.iloc[0]["guildAssociations"][pos] == "all": 
            assocs = uRow.iloc[0]["guildAssociations"]
            assocs[pos] = [guildID]
            uRow.at[0,"guildAssociations"] = assocs
        else: 
            x = uRow.iloc[0]["guildAssociations"][0].append(guildID)
            uRow.at[0,"guildAssociations"] = x
    #Reformat data as necessary
    uRow.at[0,"guildAssociations"] = str(uRow.iloc[0]["guildAssociations"])
    uRow["charIDs"] = uRow["charIDs"].astype("str")
    uRow["guildAssociations"] = uRow["guildAssociations"].astype("str")
    uRow["readonly"] = uRow["readonly"].astype("str")
    gRow["guildIDs"] = gRow["guildIDs"].astype("str")
    gRow["mainCharIDs"] = gRow["mainCharIDs"].astype("str")
    print(gRow.dtypes)
    #Save the data!
    print("Saving data.") #debug
    if concat: #If the stuff wasn't found before, then append to existing.
        print("Concatenating.")
        uRow.to_sql(name='users',con=connection,if_exists="append")
        print("1/2")
        gRow.to_sql(name='guilds',con=connection,if_exists="append")
        print("Concatenated.")
    else: #Otherwise, just update the table by replacement.
        users.to_sql(name='users',con=connection,if_exists="replace")
        guilds.to_sql(name='guilds',con=connection,if_exists="replace")
    #Construct a nice pretty message.
    #name = "NAME_PLACEHOLDER"
    message += name
    if readonly: message += " (read only)"
    else: message += " (writable)"
    message += " with ID `"+token+"` to be associated with "
    if allguilds: message += "**all** guilds"
    else: message += "**this** guild"
    if default: message += " and function as the default for this guild"
    message += "."
    if readonly: message += " In order to give the bot write access to your character sheet, please give editor status to its email and run this command again. Bot email: `discord-test@dungeon-ai-416903.iam.gserviceaccount.com`."
    await interaction.response.send_message(message,ephemeral=True)

#view
#view links for your (or specified) account
@tree.command(
    name="view",
    description="View a list of your character associations for this guild."
)
@discord.app_commands.describe(
    char="'all,' ID,  or comma-separated list of IDs of characters you wish to view. (Default: all)",
    private="Hide the message from other users in this server. (Default: True)"
)
async def view(interaction: discord.Interaction, char: str="all",private: bool=True):
    message = "Characters found: \n =============== \n **ID | Name | default? | guild association | bot access \n"
    guildID = interaction.guild.id
    if interaction.user.id not in pd.to_numeric(users["userID"]).values:
        await interaction.response.send_message("You have not yet linked any characters!",ephemeral=private)
        return
    else:
        gRow = guilds.loc[guilds['userID'] == interaction.user.id]
        uRow = users.loc[users['userID'] == interaction.user.id]
    if guildID not in gRow["guildIDs"]:
        #Check later for any with 'all'
        pass
    if char == "all":
        charlist = uRow["charIDs"]
    else: charlist = char.replace(" ","").split(",")
    for character in charlist:
        message += "`"+character+"` | "
        message += str(sheet.values().get(spreadsheetId=character,range="Character Sheet!C2").execute().get("values",[])) + " | "
        pos = uRow.iloc[0]["charIDs"].index(character)
        message += str(gRow.iloc[0]["mainCharIDs"][gRow.iloc[0]["guildIDs"].index(guildID)]) + " | "
        #default status
        guildassocs = uRow.iloc[0]["guildAssociations"][pos]
        if len(guildassocs) > 1: #If there are multiple,
            message += "Multiple, including this one"
        elif guildID in guildassocs: #If there's just one, and it's this one,
            message += "This guild only"
        elif guildassocs == all:
            message += "All guilds"
        else:
            raise ValueError("Something's wrong with guildassocs, which has value "+str(guildassocs))
        if readonlytest: message += "read only"
        else: message += "writable"
    await interaction.response.send_message(message,ephemeral=private)

#async def unlink()
#Let someone unlink data.

#Other commands to write:
#skillroll (roll the associated skill+modifiers, this is the main function we want)
#requestroll (be able to request players click a button and roll a thing.)
#configure (bot settings per server, maybe uses a third table, things like who can view sheets and request rolls.)
