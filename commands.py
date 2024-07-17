"""
commands

This module contains the commands usable through discord with the Dungeon AI bot. 
"""

#Imports
import discord, re
import googleapiclient.errors
import numpy as np
import pandas as pd
from decs import *
from table2ascii import table2ascii as t2a

#Setup
users = pd.read_sql("SELECT "+", ".join(userCols)+" FROM users",connection,dtype=types)
#chars = pd.read_sql("SELECT "+", ".join(charCols)+" FROM chars",connection)
guilds = pd.read_sql("SELECT "+", ".join(guildCols)+" FROM guilds",connection,dtype=types)

#List of commands. Important!
@tree.command(
    #name="help",description="Lists available commands" #moved to docstring
)
async def help(interaction: discord.Interaction):
    """
    Lists available commands.
    """
    embed = discord.Embed(title="Commands")
    embed.add_field(name="help",value="Prints this help menu.",inline=False)
    embed.add_field(name="roll [dice] [goal] [private]",value="Rolls a die.",inline=False)
    embed.add_field(name="link <url> [default] [allguilds]",value="Link a character sheet to your user.",inline=False)
    embed.add_field(name="view [char]",value="View the character sheets that you've linked.",inline=False)
    embed.add_field(name="unlink <char>",value="Unlink characters from yourself.",inline=False)
    await interaction.response.send_message(embed=embed,ephemeral=True)

#Basic die rolls.
@tree.command(
    #name="roll", description="Default: rolls 1d20. Rolls a number of dice with minimum, maximum, and modifier." #moved to docstring
)
#@discord.app_commands.describe(
#    dice="String representing the dice rolled, in format `XdY+Z`, `XdY-Z`, or `XdY`. (Default: 1d20)",
#    goal="Value to meet or exceed.",
#    private="Hide roll from other users. (Default: False)"
    #mod="Modifier for the die roll.",
    #high="Maximum value of the dice rolled (for XdY, this is Y).",
    #low="Minimum value of the dice rolled (for normal dice, this is 1).",
    #numdice="How many dice to roll (for XdY, this is X)."
#)
async def roll(interaction: discord.Interaction, dice: str="", goal: int=None, private: bool=False):#, mod: int=0, high: int=20, low: int=1, numdice: int=1): #don't really need all these anymore.
    """
    Default: rolls 1d20. Rolls a number of dice with minimum, maximum, and modifier.

    Parameters
    dice: str
        String representing the dice rolled, in format `XdY+Z`, `XdY-Z`, or `XdY`. (Default: 1d20)
    goal: int
        Value to meet or exceed when rolling. Reports back success/failure if given. (Optional)
    private: bool
        Hide your roll and result from other users. (Default: False)
    ----------
    """
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
    #name="link", description="Links a character sheet to your user on this server. If already linked, modifies link settings."
) #moved to docstring
#@discord.app_commands.describe(
#    url="The URL of your character sheet.",
#    default="Set the character sheet as your default character sheet for the current guild. (Default: True)",
#    allguilds="Access this character sheet from all Discord servers you are in. (Default: False).",
#)
async def link(interaction: discord.Interaction, url: str="", default: bool=True, allguilds: bool=False):
    """
    Links a character sheet to your user on this server. If already linked, modifies link settings.

    Parameters
    ----------
    url: str
        The URL or token of your character sheet. (Required)
    default: bool
        Set the character sheet as your default character sheet for the current server. (Default: True)
    allguilds: bool
        Make this character sheet accessible from all Discord servers you are in (Default: False)
    """
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
    uID = interaction.user.id
    print(type(uID),users["userID"].values,uID in users["userID"].values)
    if interaction.user.id not in users["userID"].values:
        gRow = pd.DataFrame([[interaction.user.id,[],[]]],columns=guildCols) #fill placeholders in a moment
        uRow = pd.DataFrame([[interaction.user.id,[],[[]],[]]],columns=userCols)
        message = "Linked "
        concat = True

        cIDs = uRow.iloc[0]["charIDs"]
        gAssoc = uRow.iloc[0]["guildAssociations"]
        gIDs = gRow.iloc[0]["guildIDs"]
        mcIDs = gRow.iloc[0]["mainCharIDs"]
        roArray = uRow.iloc[0]["readonly"]
    else:
        #Pull up the existing data.
        gRow = guilds.loc[guilds['userID'] == interaction.user.id]
        uRow = users.loc[users['userID'] == interaction.user.id]
        #Setup
        message = "Updated "
        concat = False
        #Parse the information that was present
        cIDs = strtolist(uRow.iloc[0]["charIDs"])
        gAssoc = strtolist(uRow.iloc[0]["guildAssociations"])
        gAssoc = [strtolist(x) for x in gAssoc]
        gIDs = strtolist(gRow.iloc[0]["guildIDs"])
        gIDs = [int(x) for x in gIDs]
        mcIDs = strtolist(gRow.iloc[0]["mainCharIDs"])
        roArray = strtolist(uRow.iloc[0]["readonly"])
        #See if the token is already associated with this guild and allguild and default statuses are not changing, and that the readonly status wouldn't change.
        if gAssoc[pos] != "all": 
            print(gAssoc)
            gAssoc[pos] = [int(x) for x in gAssoc[pos]]
        print("anything to do? \n",guildID in gAssoc[pos] and not allguilds,readonly,roArray[pos] == False)
        if ((guildID in gAssoc[pos] and not allguilds) or (gAssoc[pos] == "all" and allguilds)) and readonly == (roArray[pos] == "True"):
            print("checking default",mcIDs[gIDs.index(guildID)],default,token in mcIDs[gIDs.index(guildID)])
            if (token in mcIDs[gIDs.index(guildID)]) == default:
                await interaction.response.send_message("This character is already linked as described. Nothing to do!",ephemeral=True)
                return
    if False: #commenting these out for now until char db set up -- which is maybe never!
        if token not in chars["charID"]: 
            cRow = [token] 
            #do stuff to generate the character in the database
        else: #go ahead and force update while we're here
            #update the character
            pass
    #See if the character is already in the table
    
    if token not in cIDs: 
        cIDs.append(token)
        uRow.at[0,"charIDs"] = cIDs
    pos = cIDs.index(token) #Store where in the row it is.
    print(cIDs,len(cIDs),cIDs[0],token,pos)
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
    #Update read-only status now that it's been checked.
    try:
        roArray[pos] = readonly
    except IndexError: #Unless it's not in the list yet.
        roArray.append(readonly)
    uRow.at[0,"readonly"] = roArray
    #See if we need to add the current guild to the list of guilds.
    if guildID not in gIDs: 
        gIDs.append(guildID)
    #If this character is to be the default for this guild, we should associate them.
    if default: 
        try: #Try reassigning if exists
            mcIDs[gIDs.index(guildID)] = token
        except IndexError: #If it doesn't, create it.
            mcIDs.append(token)
            if len(mcIDs) < gIDs.index(guildID): #If we still don't have that many indices,
                raise ValueError("Your character database is corrupted. Please copy down the information you can with `/view char:all`, clear your database with `/unlink char:all`, and recreate it. Please also [submit a bug report on our GitHub](https://github.com/nuclearGoblin/Dungeon-AI).")
    else:
        try: #Try reassigning if exists
            mcIDs[gIDs.index(guildID)] = None
        except:
            mcIDs.append(None)
            if len(mcIDs) < gIDs.index(guildID): #If we still don't have that many indices,
                raise ValueError("Your character database is corrupted. Please copy down the information you can with `/view char:all`, clear your database with `/unlink char:all`, and recreate it. Please also [submit a bug report on our GitHub](https://github.com/nuclearGoblin/Dungeon-AI).")
    #Set up guild association for character.
    print("allguilds?",allguilds)
    #If it's set to all, overwrite the array with "all"
    if allguilds: 
        assocs = uRow.iloc[0]["guildAssociations"]
        assocs[pos] = "all"
        uRow.at[0,"guildAssociations"] = assocs
    #If it's not set to all,
    elif guildID not in gAssoc[pos]:
        #If it was previously set to all, overwrite.
        if gAssoc[pos] == "all": 
            assocs = uRow.iloc[0]["guildAssociations"]
            assocs[pos] = [guildID]
            uRow.at[0,"guildAssociations"] = assocs
        else: #Otherwise, append
            x = gAssoc[pos]
            x.append(guildID)
            uRow.at[0,"guildAssociations"] = x
    print("guildassoc:",gAssoc)
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

    #Reload edited databases.
    users = pd.read_sql("SELECT "+", ".join(userCols)+" FROM users",connection,dtype=types)
    guilds = pd.read_sql("SELECT "+", ".join(guildCols)+" FROM guilds",connection,dtype=types)

#view
#view links for your (or specified) account
@tree.command(
    #name="view", description="View a list of your character associations for this guild."
) #moved to docstring
#@discord.app_commands.describe(
#    char="'all', 'guild', ID,  or comma-separated list of IDs of characters you wish to view. (Default: guild)",
#    private="Hide the message from other users in this server. (Default: True)"
#)
async def view(interaction: discord.Interaction, char: str="guild",private: bool=True):
    """
    View a list of your characters.

    Parameters
    ----------
    char: str
        "'all', 'guild', ID,  or comma-separated list of IDs of characters you wish to view. (Default: guild)",
    private: bool
        Hide the message from other users in this server. (Default: True)
    """
    header = ["Name","ID","Default?","Guild(s)","Bot Access"]
    #message = "Characters found: \n =============== \n **ID | Name | default? | guild association | bot access** \n"
    guildID = str(interaction.guild.id)
    if interaction.user.id not in pd.to_numeric(users["userID"]).values:
        await interaction.response.send_message("You have not yet linked any characters!",ephemeral=private)
        return
    else:
        gRow = guilds.loc[guilds['userID'] == interaction.user.id]
        uRow = users.loc[users['userID'] == interaction.user.id]
    if any("all" in x for x in strtolist(uRow["guildAssociations"])):
        allspresent = True
    else: allspresent = False
    if char == "guild":
        if guildID not in strtolist(gRow.iloc[0]["guildIDs"]) and not allspresent: #If you asked for everything in this guild but there's nothing,
            await interaction.response.send_message("You do not have any characters linked in this guild. Run with char set to `all` to view all linked characters.",ephemeral=private)
            return
        #print(uRow["charIDs"].values,strtolist(uRow["charIDs"].values)[0],strtolist(strtolist(uRow["charIDs"].values)[0]),strtolist(strtolist(uRow["charIDs"].values)[0])[0])
        #for x in strtolist(uRow["charIDs"].values)[0]: print(x)
        charlist = strtolist(strtolist(uRow["charIDs"].values)[0])
        #Then prune the list.
        for character in charlist:
            pos = strtolist(uRow.iloc[0]["charIDs"]).index(character)
            gAssoc = strtolist(uRow.iloc[0]["guildAssociations"])[pos]
            if type(gAssoc) == str: gAssoc = [gAssoc]
            gAssoc = [int(x) for x in gAssoc]
            if int(guildID) not in gAssoc and "all" not in gAssoc: charlist.remove(character)
    elif char == "all": charlist = strtolist(uRow["charIDs"].values)
    else: charlist = char.replace(" ","").split(",")
    body = []
    for character in charlist:
        try: #Check that the character sheet is readable
            name = str(sheet.values().get(spreadsheetId=character,range="Character Sheet!C2").execute().get("values",[])[0][0])
        except HttpError:
            name = "(Unreachable)"
        row = [name,character,None,None,None]
        try: #Check that the character sheet is associated with the user.
            pos = strtolist(uRow.iloc[0]["charIDs"]).index(character)
        except ValueError: #If it's not,
            continue #Skip this iteration.
        mcIDs = strtolist(gRow.iloc[0]["mainCharIDs"])
        gIDs = strtolist(gRow.iloc[0]["guildIDs"])
        #default status
        try: row[2] = str(mcIDs[gIDs.index(guildID)] == character)
        except IndexError: #If it's not associated with this guild
            row[2] = "N/A"
        gAssoc = strtolist(uRow.iloc[0]["guildAssociations"])[pos]
        if type(gAssoc) == str: gAssoc = [gAssoc]
        gAssoc = [int(x) for x in gAssoc]
        if len(gAssoc) > 1 and int(guildID) in gAssoc: #If there are multiple,
            row[3] = "Multiple, including this one"
        elif int(guildID) in gAssoc: #If there's just one, and it's this one,
            row[3] = "This guild only"
        elif gAssoc == "all": row[3] = "All guilds"
        else: #Assume that it's a list that doesn't contain the current guild and print it.
            row[3] = str(gAssoc)
        if name != "(Unreachable)":
            if readonlytest(character): row[4] = "Read Only"
            else: row[4] = "Writable"
        else:
            row[4] = "No Access"
        body.append(row)
    output = t2a(header=header,body=body,first_col_heading=True)
    #await interaction.response.send_message(message,ephemeral=private)
    await interaction.response.send_message(f"**Characters found:**\n```\n"+output+"\n```",ephemeral=private)

#async def unlink()
#Let someone unlink data.
@tree.command(
    #name="unlink", description="Unlink one or more characters from yourself."
) #moved to docstring
#@discord.app_commands.describe(
#    char="'all', 'guild', a character ID, or a comma-separated list of IDs. (Required)"
#)
async def unlink(interaction: discord.Interaction, char: str):
    """
    Unlink one or more characters from yourself.

    Parameters
    ----------
    char: str
        'all', 'guild', a character ID, or a comma-separated list of IDs. (Required)
    """
    global users,guilds
    if char == "all":
        #delete everything
        users = users[users["userID"] != interaction.user.id]
        guilds = guilds[guilds["userID"] != interaction.user.id]
        users.to_sql(name='users',con=connection,if_exists="replace")
        guilds.to_sql(name='guilds',con=connection,if_exists="replace")
        await interaction.response.send_message("All of your user data was deleted from the bot's database.",ephemeral=True)
        #Reload edited databases.
        users = pd.read_sql("SELECT "+", ".join(userCols)+" FROM users",connection,dtype=types)
        guilds = pd.read_sql("SELECT "+", ".join(guildCols)+" FROM guilds",connection,dtype=types)
        return
    guildID = str(interaction.guild.id)
    #Pull up the existing data.
    gRow = guilds.loc[guilds['userID'] == interaction.user.id]
    uRow = users.loc[users['userID'] == interaction.user.id]
    #Parse the information that was present
    cIDs = strtolist(uRow.iloc[0]["charIDs"])
    gAssoc = strtolist(uRow.iloc[0]["guildAssociations"])
    gAssoc = [strtolist(x) for x in gAssoc]
    gIDs = strtolist(gRow.iloc[0]["guildIDs"])
    gIDs = [int(x) for x in gIDs]
    mcIDs = strtolist(gRow.iloc[0]["mainCharIDs"])
    roArray = strtolist(uRow.iloc[0]["readonly"])
    if char == "guild":
        #find everything associated only with this guild, and construct a list
        charlist = []
        for i,x in enumerate(cIDs):
            if gAssoc[i] == [guildID]: charlist.append(x)
            elif guildID in gAssoc[i]: #For things with multiple guild associations, remove this guild's instance.
                #remove the association, but not the character
                gAssoc[i].remove(guildID) #delete that entry from this list 
                uRow.at[0,"guildAssociations"] = gAssoc #and rewrite into uRow
                pass
        #Now delete this guild from gRow
        #print(gIDs,guildID,guildID in gIDs,type(gIDs[0]),type(guildID)) #debug
        try:
            gloc = gIDs.index(guildID)
        except ValueError: #Assume that it's a type mismatch
            guildID = int(guildID)
            try:
                gloc = gIDs.index(guildID)
            except ValueError: #If it's not, then there's nothing to do.
                await interaction.response.send_message("There is no character data associated with this guild.")
                return
        gIDs.pop(gloc); mcIDs.pop(gloc)
        gRow.at[0,"guildIDs"] = gIDs
        #gRow.at[0,"mainCharIDs"] = mcIDs #We're doing this again later, so save the processor some work.
    else:
        #parse the list
        charlist = char.replace(" ","").split(",")
    
    #Delete the main character ID from the guild list.
    for i,x in enumerate(mcIDs):
        if x in charlist: mcIDs[i] = None
    gRow.at[0,"mainCharIDs"] = mcIDs
    
    #Now do the one-by-one deletion from the users.
    print(uRow,charlist)
    unfound = []
    for x in charlist:
        try:
            pos = cIDs.index(x)
            if char != "guild":
                print(gRow.at[0,'mainCharIDs'],gRow["mainCharIDs"],type(gRow.at[0,'mainCharIDs']))
                print(gRow.keys(),uRow.keys())
                print(gRow)
                print("Pop...")
                mcIDs.pop(pos)
                #gRow.at[0,"mainCharIDs"] = gtemp.pop(pos)
                print(mcIDs)
                print("Pop!")
            print(uRow)
            print(type(uRow.at[0,"charIDs"]))
            cIDs.pop(pos); gAssoc.pop(pos); roArray.pop(pos)
            print(gAssoc)
            #print(uRow) #Not updated yet
        except ValueError: #It's not there
            unfound.append(x)
            charlist.remove(x)
    
    #Remove empty guilds
    emptyguilds = 0
    for guildID in gIDs:
        #if guild is not associated with anything,
        for lst in gAssoc:
            if str(guildID) not in lst and guildID not in lst:
                #delete it.
                try:
                    gloc = gIDs.index(guildID)
                except ValueError: #Assume that it's a type mismatch
                    guildID = int(guildID)
                    try:
                        gloc = gIDs.index(guildID)
                    except ValueError: #If it's not, then there's nothing to do.
                        await interaction.response.send_message("There is no character data associated with this guild.")
                        return
                gIDs.pop(gloc); mcIDs.pop(gloc)
                gRow.at[0,"guildIDs"] = gIDs
                emptyguilds += 1

    gRow.at[0,"mainCharIDs"] = str(mcIDs)
    uRow.at[0,"charIDs"] = str(cIDs)
    uRow.at[0,"guildAssociations"] = str(gAssoc)
    uRow.at[0,"readonly"] = str(roArray)

    #Rewrite gRow,uRow to the users,guilds
    
    #And then those to the database
    #Reload edited databases.
    users = pd.read_sql("SELECT "+", ".join(userCols)+" FROM users",connection,dtype=types)
    guilds = pd.read_sql("SELECT "+", ".join(guildCols)+" FROM guilds",connection,dtype=types)
    message = "The following character IDs were unlinked: "+str(charlist)+"."
    if unfound: message += " The following character IDs were specified but not found for removal: "+str(unfound)+"."
    if emptyguilds: 
        message += " "+str(emptyguilds)+" guild"
        if emptyguilds>1: message += "s no longer have"
        else: message += " no longer has"
        message += " linked characters after this."
    await interaction.response.send_message(message,ephemeral=True)

#Other commands to write:
#verify (check the read/writability of a character sheet and update the db entry if necessary)
# - this is a feature I see other functions using so make it its own function
#skillroll (roll the associated skill+modifiers, this is the main function we want)
# - functions within this will be called by skillroll
#requestroll (be able to request players click a button and roll a thing.)
#configure (bot settings per server, maybe uses a third table, things like who can view sheets and request rolls.)