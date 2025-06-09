"""
commands

This module contains the commands usable through discord with the Dungeon AI bot. 
"""

#Imports
import discord, re
import googleapiclient.errors
import numpy as np
import pandas as pd
import decs as d
#from decs import *
from table2ascii import table2ascii as t2a

#Setup/things we want to keep in memory
users = pd.read_sql("SELECT "+", ".join(d.userCols)+" FROM users",d.connection,dtype=d.types)
#chars = pd.read_sql("SELECT "+", ".join(charCols)+" FROM chars",connection)
guilds = pd.read_sql("SELECT "+", ".join(d.guildCols)+" FROM guilds",d.connection,dtype=d.types)

#List of commands. Important!
@d.tree.command(
    #name="help",description="Lists available commands" #moved to docstring
)
async def help(interaction: discord.Interaction):
    """
    Lists available commands.
    """
    embed = discord.Embed(title="Commands")
    embed.add_field(name="help",value="Prints this help menu.",inline=False)
    embed.add_field(name="roll [dice] [goal] [autoexp] [private]",value="Rolls a die.",inline=False)
    embed.add_field(name="link <url> [default] [allguilds]",value="Link a character sheet to your user.",inline=False)
    embed.add_field(name="view [char]",value="View the character sheets that you've linked.",inline=False)
    embed.add_field(name="unlink <char>",value="Unlink characters from yourself.",inline=False)
    await interaction.response.send_message(embed=embed,ephemeral=True)

#Basic die rolls.
@d.tree.command()
async def roll(interaction: discord.Interaction, modifier: str="", goal: int=None, exp: bool=False, private: bool=False):
    """
    Rolls 1d20 with provided modifiers. Default modifier: 0.

    Parameters
    modifier: str
        String representing modifier, in format `X+skill+stat+Y`. (Default: 0. Example: `coolness+charisma+8`)
        Calls your default character if non-numeric values are provided.
    goal: int
        Value to meet or exceed when rolling. Reports back success/failure if given. (Optional)
    autoexp: bool
        Automatically grant exp for attempting the roll, if applicable. (Default: False)
    private: bool
        Hide your roll and result from other users. (Default: False)
    ----------
    """
    button_view = None #unless defined
    global users,guilds

    parsed_mod = d.mod_parser(modifier,goal,autoexp,interaction,guilds,users)
    if parsed_mod == 1:
        await interaction.response.send_message(
            "`modifier` argument format not recognized. "
            + "Please follow the format `skillname+statname+X`,"
            + "ex `coolness+charisma-13`.",ephemeral=True)
        return 1
    elif parsed_mod == 2:
        await interaction.response.send_message(
            "You appear to have selected a skill name, "
            + "but you have no default character sheet for me to check. "
            + "Please either set a default character sheet using `/link` "
            + "or double-check your roll syntax.",ephemeral=True)
        return 1
    _,rollname,skillname,skillrow,rank,token,_,button_view = parsed_mod

    await interaction.response.send_message(rollname,ephemeral=private,view=button_view)

#Character sheet linking
@d.tree.command(
    #name="link", description="Links a character sheet to your user on this server. If already linked, modifies link settings."
) #moved to docstring
async def link(interaction: discord.Interaction, url: str="", default: bool=True, allguilds: bool=False):
    """
    Links a character sheet to your user on this server. If already linked, modifies link settings.

    Parameters
    ----------
    url: str
    
    print("users:",users)The URL or token of your character sheet. (Required)
    default: bool
        Set the character sheet as your default character sheet for the current server. (Default: True)
    allguilds: bool
        Make this character sheet accessible from all Discord servers you are in (Default: False)
    """
    #Want to make sure we are updating the global var.
    global users,guilds#,chars

    #Token interpretation
    if "." in url: #This is a full URL, so we need to strip it
        token = url.split("https://") #Remove this first if it's present, since we're splitting on / this would cause issues.
        token = url.replace('?','/').split("/") #Now split along slashes and ?s
        token = token[5] #Take the nth entry
    elif "/" in url: #I don't know how to interpret this. You left out .com but included slashes so I don't know where to start.
        await interaction.response.send_message("Unable to interpret provided url. Please either provide the full URL of your document or only the token.",ephemeral=True)
        return
    else: 
        token = url
    #Test write to the character sheet.
    readonly = d.readonlytest(token)
    #Now that we have a token, see if the user is in the table.
    #uID = interaction.user.id
    guildID = str(interaction.guild.id)
    if interaction.user.id not in users["userID"].values:
        gRow = pd.DataFrame([[interaction.user.id,[],[]]],columns=d.guildCols) #fill placeholders in a moment
        uRow = pd.DataFrame([[interaction.user.id,[],[[]],[]]],columns=d.userCols)
        #message = "Linked "
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
        cIDs = d.strtolist(uRow.iloc[0]["charIDs"])
        gAssoc = d.strtolist(uRow.iloc[0]["guildAssociations"])
        gAssoc = [d.strtolist(x) for x in gAssoc]
        gIDs = d.strtolist(gRow.iloc[0]["guildIDs"])
        mcIDs = d.strtolist(gRow.iloc[0]["mainCharIDs"])
        roArray = d.strtolist(uRow.iloc[0]["readonly"])
    
    print("\n========================\n")
    print("Row init \n",gRow["mainCharIDs"])

    #Test read the character sheet.
    try:
        name = d.retrievevalue(location=d.statlayoutdict["name"],token=token)
    except googleapiclient.errors.HttpError:
        await interaction.response.send_message(
            "Unable to reach character sheet. Please make sure that it is either public or shared with the bot, whose email is: `"
            +d.botmail+"`. If you provided a complete url, try providing only the token. "
            +d.bugreporttext+" if that resolves the issue."
        )
        return
    #See if the character is already in the table
    if token not in cIDs: 
        cIDs.append(token)
        uRow.at[0,"charIDs"] = cIDs
        pos = cIDs.index(token) #Store where in the row it is.
        message = "Linked "
    else:
        pos = cIDs.index(token)
        #See if the token is already associated with this guild and allguild and default statuses are not changing, and that the readonly status wouldn't change.
        if gAssoc[pos] not in ["all",["all"]]:
            gAssoc[pos] = [int(x) for x in gAssoc[pos]]
        if ((guildID in gAssoc[pos] and not allguilds) or (gAssoc[pos] == "all" and allguilds)) and readonly == (roArray[pos] == "True"):
            if (token in mcIDs[gIDs.index(guildID)]) == default:
                await interaction.response.send_message("This character is already linked as described. Nothing to do!",ephemeral=True)
                return
    #Update read-only status now that it's been checked.
    try:
        roArray[pos] = readonly
    except IndexError: #Unless it's not in the list yet.
        roArray.append(readonly)
    uRow.at[0,"readonly"] = roArray
    #See if we need to add the current guild to the list of guilds.
    if guildID not in gIDs:
        gIDs.append(guildID)
        gRow.at[0,"guildIDs"] = gIDs
    #If this character is to be the default for this guild, we should associate them.
    if default: 
        try: #Try reassigning if exists
            mcIDs[gIDs.index(guildID)] = token
        except IndexError: #If it doesn't, create it.
            mcIDs.append(token)
            print("mcIDs:",mcIDs)
            if len(mcIDs) < gIDs.index(guildID): #If we still don't have that many indices,
                raise ValueError("Your character database is corrupted. Please copy down the information you can with `/view char:all`, clear your database with `/unlink char:all`, and recreate it. Please also [submit a bug report on our GitHub](https://github.com/nuclearGoblin/Dungeon-AI).")
    else:
        try: #Try reassigning if exists
            mcIDs[gIDs.index(guildID)] = None
        except IndexError:
            mcIDs.append(None)
            if len(mcIDs) < gIDs.index(guildID): #If we still don't have that many indices,
                raise ValueError("Your character database is corrupted. Please copy down the information you can with `/view char:all`, clear your database with `/unlink char:all`, and recreate it. Please also [submit a bug report on our GitHub](https://github.com/nuclearGoblin/Dungeon-AI).")
    gRow.at[0,"mainCharIDs"] = mcIDs #Update the info!
    print("gRow[mcids]:",gRow.at[0,"mainCharIDs"])
    #Set up guild association for character.
    #If it's set to all, overwrite the array with "all"
    if allguilds: 
        assocs = d.strtolist(uRow.iloc[0]["guildAssociations"])
        if len(assocs) <= pos:
            assocs.append("all")
        else:
            assocs[pos] = "all"
        uRow.at[0,"guildAssociations"] = assocs
        default = False #I don't know what this would mean.
    #If it's not set to all,
    elif len(gAssoc) <= pos: 
        gAssoc.append([guildID])
        uRow.at[0,"guildAssociations"] = [str(gAssoc)]
    elif guildID not in gAssoc[pos]:
        #If it was previously set to all, overwrite.
        if gAssoc[pos] == "all": 
            assocs = uRow.iloc[0]["guildAssociations"]
            assocs[pos] = [guildID]
            uRow.at[0,"guildAssociations"] = assocs
        else: #Otherwise, append
            x = gAssoc[pos]
            x.append(int(guildID))
            print("x",x)
            uRow.at[0,"guildAssociations"] = [x]
    #Reformat data as necessary
    uRow["guildAssociations"] = uRow["guildAssociations"].astype(str)
    print("gA:", uRow["guildAssociations"])
    uRow["charIDs"] = uRow["charIDs"].astype("str")
    uRow["guildAssociations"] = uRow["guildAssociations"].astype("str")
    uRow["readonly"] = uRow["readonly"].astype("str")
    gRow["guildIDs"] = gRow["guildIDs"].astype("str")
    gRow["mainCharIDs"] = gRow["mainCharIDs"].astype("str")
    #Save the data!
    if concat: #If the stuff wasn't found before, then append to existing.
        uRow.to_sql(name='users',con=d.connection,if_exists="append")
        gRow.to_sql(name='guilds',con=d.connection,if_exists="append")
    else: #Otherwise, just update the table by replacement.
        print("uRow:\n",uRow)
        guilds.loc[guilds['userID'] == interaction.user.id] = gRow
        users.loc[users['userID'] == interaction.user.id] = uRow
        users.to_sql(name='users',con=d.connection,if_exists="replace")
        guilds.to_sql(name='guilds',con=d.connection,if_exists="replace")
    #Construct a nice pretty message.
    #name = "NAME_PLACEHOLDER"
    message += "**"+name+"**"
    if readonly: 
        message += " (read only)"
    else: 
        message += " (writable)"
    message += " with ID `"+token+"` to be associated with "
    if allguilds: message += "**all** guilds"
    else: message += "**this** guild"
    if default: message += " and function as the default for this guild"
    message += "."
    if readonly: 
        message += (
            " In order to give the bot write access to your character sheet, "
            +"please give editor status to its email and run this command again. Bot email: `"
            +d.botmail+"`."
        )
    await interaction.response.send_message(message,ephemeral=True)

    #Reload edited databases.
    users = pd.read_sql("SELECT "+", ".join(d.userCols)+" FROM users",d.connection,dtype=d.types)
    guilds = pd.read_sql("SELECT "+", ".join(d.guildCols)+" FROM guilds",d.connection,dtype=d.types)

#view
#view links for your (or specified) account
@d.tree.command(
    #name="view", description="View a list of your character associations for this guild."
) #moved to docstring
#@discord.app_commands.describe(
#    char="'all', 'guild', ID,  or comma-separated list of IDs of characters you wish to view. (Default: guild)",
#    private="Hide the message from other users in this server. (Default: True)"
#)
async def view(interaction: discord.Interaction, char: str="guild"):
    """
    View a list of your characters.

    Parameters
    ----------
    char: str
        "'all', 'guild', ID,  or comma-separated list of IDs of characters you wish to view. (Default: guild)",
    """
    
    print("view ++++++++++++++++++++")

    private = True #I am forcing these to be private because it means fewer options for users to deal with.
    header = ["Name","ID","Default?","Guild(s)","Bot Access"]
    #message = "Characters found: \n =============== \n **ID | Name | default? | guild association | bot access** \n"
    guildID = str(interaction.guild.id)
    if interaction.user.id not in pd.to_numeric(users["userID"]).values:
        await interaction.response.send_message("You have not yet linked any characters!",ephemeral=private)
        return
    else:
        gRow = guilds.loc[guilds['userID'] == interaction.user.id]
        uRow = users.loc[users['userID'] == interaction.user.id]
    if any("all" in x for x in d.strtolist(uRow["guildAssociations"])):
        allspresent = True
    else: 
        allspresent = False
    if char == "guild":
        if guildID not in d.strtolist(gRow.iloc[0]["guildIDs"]) and not allspresent: #If you asked for everything in this guild but there's nothing,
            await interaction.response.send_message("You do not have any characters linked in this guild. Run with char set to `all` to view all linked characters.",ephemeral=private)
            return
        charlist = d.strtolist(d.strtolist(uRow["charIDs"].values)[0])
        #Then prune the list.
        for character in charlist:
            pos = d.strtolist(uRow.iloc[0]["charIDs"]).index(character)
            for x in d.strtolist(uRow.iloc[0]["guildAssociations"]):
                print(x)
            gAssoc = d.strtolist(uRow.iloc[0]["guildAssociations"])[pos]
            print(gAssoc)
            if (type(gAssoc) == str): 
                gAssoc = [gAssoc]
            gAssoc = d.assocformat(gAssoc)
            if int(guildID) not in gAssoc and "all" not in gAssoc: 
                charlist.remove(character)
    elif (char == "all") or allspresent: 
        charlist = d.strtolist(uRow["charIDs"].values)
        charlist_temp = []
        for char in charlist:
            for subchar in d.strtolist(char):
                charlist_temp.append(subchar)
        #charlist = list(set(charlist)) #kill duplicates
        charlist = charlist_temp
        print(charlist,type(charlist))
        #print(charlist) #looks good here
    else: 
        charlist = char.replace(" ","").split(",")
    body = []
    for character in charlist:
        print(character,type(character),character[0])
        try: #Check that the character sheet is readable
            name = str(d.sheet.values().get(spreadsheetId=character,range="Character Sheet!C2").execute().get("values",[])[0][0])
        except IndexError:
            name = "NOT_FOUND"
        except googleapiclient.errors.HttpError:
            name = "(Unreachable)"
        print(character, name) #'all' leads to unreachable
        row = [name,character,None,None,None]
        try: #Check that the character sheet is associated with the user.
            pos = d.strtolist(uRow.iloc[0]["charIDs"]).index(character)
        except ValueError: #If it's not,
            continue #Skip this iteration.
        mcIDs = d.strtolist(gRow.iloc[0]["mainCharIDs"])
        gIDs = d.strtolist(gRow.iloc[0]["guildIDs"])
        #default status
        try:
            print("mcIDs:",mcIDs,"gIDs:",gIDs)
            row[2] = str(mcIDs[gIDs.index(guildID)] == character)
        except ValueError: #If it's not associated with this guild
            row[2] = "N/A"
        except IndexError:
            pass #TODO: add a user-oriented bug message 
        gAssoc = d.strtolist(uRow.iloc[0]["guildAssociations"])[pos]
        if type(gAssoc) is str: 
            gAssoc = [gAssoc]
        gAssoc = d.assocformat(gAssoc)
        if len(gAssoc) > 1 and int(guildID) in gAssoc: #If there are multiple,
            row[3] = "Multiple, including this one"
        elif int(guildID) in gAssoc: #If there's just one, and it's this one,
            row[3] = "This guild only"
        elif gAssoc == "all": row[3] = "All guilds"
        else: #Assume that it's a list that doesn't contain the current guild and print it.
            row[3] = str(gAssoc)
        if name != "(Unreachable)":
            if d.readonlytest(character): row[4] = "Read Only"
            else: row[4] = "Writable"
        else:
            row[4] = "No Access"
        body.append(row)
    output = t2a(header=header,body=body,first_col_heading=True)
    #await interaction.response.send_message(message,ephemeral=private)
    await interaction.response.send_message(f"**Characters found:**\n```\n"+output+"\n```",ephemeral=private)

#Let someone unlink data.
@d.tree.command(
    #name="unlink", description="Unlink one or more characters from yourself."
) 
async def unlink(interaction: discord.Interaction, char: str):
    """
    Unlink one or more characters from yourself.

    Parameters
    ----------
    char: str
        'all', 'guild', a character ID, or a comma-separated list of IDs. (Required)
    """
    global users,guilds
    userdel = False
    if char == "all":
        userdel = True
    guildID = str(interaction.guild.id)
    #Pull up the existing data.
    gRow = guilds.loc[guilds['userID'] == interaction.user.id]
    uRow = users.loc[users['userID'] == interaction.user.id]
    #Parse the information that was present
    cIDs = d.strtolist(uRow.iloc[0]["charIDs"])
    gAssoc = d.strtolist(uRow.iloc[0]["guildAssociations"])
    gAssoc = [d.strtolist(x) for x in gAssoc]
    gIDs = d.strtolist(gRow.iloc[0]["guildIDs"])
    gIDs = [int(x) for x in gIDs]
    mcIDs = d.strtolist(gRow.iloc[0]["mainCharIDs"])
    roArray = d.strtolist(uRow.iloc[0]["readonly"])
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
        try:
            gloc = gIDs.index(guildID)
        except ValueError: #Assume that it's a type mismatch
            guildID = int(guildID)
            try:
                gloc = gIDs.index(guildID)
            except ValueError: #If it's not, then there's nothing to do.
                await interaction.response.send_message("There is no character data associated with this guild.")
                return
        gRow.at[0,"guildIDs"] = str(gIDs)
    elif char == "all":
        charlist = cIDs.copy()
        userdel = True
    else:
        #parse the list
        charlist = char.replace(" ","").split(",")
    
    #Delete the main character ID from the guild list.
    for i,x in enumerate(mcIDs):
        if x in charlist: mcIDs[i] = None
    gRow.at[0,"mainCharIDs"] = str(mcIDs)
    
    #Now do the one-by-one deletion from the users.
    unfound = []
    #gAssoc_removed = []
    for x in charlist:
        try:
            pos = cIDs.index(x)
            #if char != "guild":    mcIDs.pop(pos) #why did I write this? that's not how any of this works.
            cIDs.pop(pos); gAssoc.pop(pos); roArray.pop(pos)

        except ValueError: #It's not there
            unfound.append(x)
            charlist.remove(x)
    
    #Remove empty guilds
    emptyguilds = 0
    for guildID in gIDs:
        #print("Checking for removal of guild",guildID)
        #if guild is not associated with anything,
        timetokill = True
        if gAssoc == []: #if all guilds were removed
            pass
        else:
            for lst in gAssoc:
                if str(guildID) not in lst and guildID not in lst:
                    pass
                    #print("guildID was unassociated.")
                else: #The only case in which we don't want to remove the guild.
                    #print("Should not be removing guild.")
                    timetokill = False
                    break
        #we didn't hit our continue block, so time to delete the guild.
        if timetokill:
            try:
                gloc = gIDs.index(guildID)
            except ValueError: #Assume that it's a type mismatch
                guildID = int(guildID)
                try:
                    gloc = gIDs.index(guildID)
                except ValueError: #If it's not, then there's nothing to do.
                    await interaction.response.send_message("There is no character data associated with the guild"+guildID)
                    return
            gIDs.pop(gloc); mcIDs.pop(gloc)
            gRow.at[0,"guildIDs"] = str(gIDs)
            gRow.at[0,"mcIDs"] = str(mcIDs)
            emptyguilds += 1
    #Finally, check if user is empty.
    if mcIDs == [] and cIDs == []:
        userdel = True
    if userdel: #Just delete the rows directly to be sure.
        users = users[users["userID"] != interaction.user.id]
        guilds = guilds[guilds["userID"] != interaction.user.id]
        users.to_sql(name='users',con=d.connection,if_exists="replace")
        guilds.to_sql(name='guilds',con=d.connection,if_exists="replace")
    else:
        uRow.at[0,"charIDs"] = str(cIDs)
        uRow.at[0,"guildAssociations"] = str(gAssoc)
        uRow.at[0,"readonly"] = str(roArray)

        #Rewrite gRow,uRow to the users,guilds 
        guilds.loc[guilds['userID'] == interaction.user.id] = gRow
        users.loc[users['userID'] == interaction.user.id] = uRow

        #And then those to the database
        users.to_sql(name='users',con=d.connection,if_exists="replace")
        guilds.to_sql(name='guilds',con=d.connection,if_exists="replace")
    #Reload edited databases.
    users = pd.read_sql("SELECT "+", ".join(d.userCols)+" FROM users",d.connection,dtype=d.types)
    guilds = pd.read_sql("SELECT "+", ".join(d.guildCols)+" FROM guilds",d.connection,dtype=d.types)
    message = "The following character IDs were unlinked: "+str(charlist)+"."
    if unfound: 
        message += (
            " The following character IDs were specified but not found for removal: "
            +str(unfound)+"."
        )
    if emptyguilds: 
        message += " "+str(emptyguilds)+" guild"
        if emptyguilds>1: 
            message += "s no longer have"
        else: 
            message += " no longer has"
        message += " linked characters after this."
    if userdel:
        message += " This action resulted in the removal of all of your user data."
    await interaction.response.send_message(message,ephemeral=True)

#Other commands to write:
#verify (check the read/writability of a character sheet and update the db entry if necessary)
# - this is a feature I see other functions using so make it its own function
#skillroll (roll the associated skill+modifiers, this is the main function we want)
# - functions within this will be called by skillroll
#configure (bot settings per server, maybe uses a third table, things like who can view sheets and request rolls.)

#### Encounter commands ####

@d.tree.command()
async def levelup(interaction: discord.Interaction):
    """
    Scan for current exp on your current default character sheet and rank/level up as appropriate.
    """

    global users,guilds
    message = ""
    button_view = None
    embed = None

    #The initial level-up message should be visible to everyone unless there are buttons, in which case it should be hidden until all operations are complete.
    private = False

    #First, pull up the default character sheet
    token = d.retrieveMcToken(str(interaction.guild.id),interaction.user.id,guilds,users)

    #Now I need to check each skill. This should be a batch job for efficiency.
    retrieve = [d.statlayoutdict["skillinfo"],
            d.statlayoutdict["level"],
            d.statlayoutdict["experience"],
            d.statlayoutdict["unspent"],
            d.statlayoutdict["stats"],
            d.statlayoutdict["currenthp"]
            ]
    currentsheet = d.sheet.values()
    skillinfo,lv,exp,unspent,stats,currenthp = currentsheet.batchGet(spreadsheetId=token,ranges=retrieve).execute()['valueRanges']
    skillinfo = skillinfo['values']
    try:
        lv = int(lv['values'][0][0])
    except KeyError: #If level is blank, assume it's 1
        lv = 1
    try:
        exp = int(exp['values'][0][0])
    except KeyError: #if exp is blank, assume it's 0
        exp = 0
    try:
        unspent = int(unspent['values'][0][0])
    except KeyError: #if unspent points are blank, assume there are none.
        unspent = 0
    try:
        currenthp = int(currenthp['values'][0][0])
    except KeyError: #if current HP is blank, assume it's full.
        currenthp = d.hp(int(stats['values'][0][1]))

    # Now that we've retrieved the values, start parsing skills for levelup requirements
    if exp >= lv:
        lv += 1
        exp = 0
        message += "You've reached level "+str(lv)+", giving you three stat points to spend. "
        unspent += 3 
    dinged = []
    for i,skill in enumerate(skillinfo): #For each skill,
        #Convert values to integers
        skill[-3] = int(skill[-3])
        skill[-1] = int(skill[-1])
        #If there's enough exp for a skill to level up, then
        if skill[-1] > d.skillTrackTable[skill[-2]][skill[-3]]:
            dinged.append([skill[0],skill[-3]]) #Note that the skill level increased,
            skillinfo[i][-1] = 0                #Reset exp for the skill to 0,
            skillinfo[i][-3] += 1               #And level up
    if len(dinged) > 0:
        message += "The following skills leveled up:\n"
        for x in dinged:
            message += "- **"+x[0]+"** "+str(x[1])+" → "+str(x[1]+1)+"\n"
    if unspent > 0:
        #Get stat info
        strength,con,dex,intellect,cha = stats['values'][0]
        #Set up embed for information about level up
        embed = discord.Embed(title="Stat Allocation",
                              description = "Points remaining: "+str(unspent),
                              url="https://docs.google.com/spreadsheets/d/"+str(token)
                              )
        embed.add_field(name="Strength",value = strength)
        embed.add_field(name="Constitution",value = con)
        embed.add_field(name="Dexterity",value=dex)
        embed.add_field(name="Intelligence",value=intellect)
        embed.add_field(name="Charisma",value=cha)
        #Pass things into buttons
        button_view = d.statAllocationButtons()
        button_view.embed = embed
        button_view.parentInter = interaction
        button_view.strength = int(strength)
        button_view.con = int(con)
        button_view.dex = int(dex)
        button_view.intellect = int(intellect)
        button_view.cha = int(cha)
        button_view.unspent = int(unspent)
        button_view.token = token
        button_view.currenthp = currenthp

        private = True

    requests = {
            'value_input_option': 'USER_ENTERED',
            'data': [
                {'range':d.statlayoutdict["skillinfo"],'values':skillinfo},
                {'range':d.statlayoutdict["level"],'values':[[lv]]},
                {'range':d.statlayoutdict["experience"],'values':[[exp]]},
                {'range':d.statlayoutdict["unspent"],'values':[[unspent]]}
            ]
            }
    currentsheet.batchUpdate(spreadsheetId=token,body=requests).execute()

    if message == "" and button_view == embed == None: #If there's nothing to do,
        message = "You're already leveled up; nothing to do!"
        private = True
    await interaction.response.send_message(message,view=button_view,embed=embed,ephemeral=private)

@d.tree.command()
async def damage(interaction: discord.Interaction, amount: int, bypass: bool=False, name: str=""):
    """
    [GM Utility] Create a button for dealing damage.
    
    Parameters
    ----------
    amount: int
        Amount of damage to deal.
    bypass: bool
        Whether or not the damage should bypass DR. (Default: false)
    name: str
        Name of the entity dealing damage. (Optional)
    """
    #Set up some variables
    global users,guilds
    message = ""

    amount = abs(amount)
    if amount <= 0: #You said explicitly to adjust by 0? why would you do that
        await interaction.response.send_message("'"+str(amount)+" damage'? Very funny.",ephemeral=True)
        return 1

    if name != "":
        message = name+" deals "
    message += str(amount)+" damage!"
    if bypass:
        message = message[:-1]+", bypassing DR!"
    
    button_view = d.takeDamage()
    button_view.message = message 
    button_view.damage = amount
    button_view.parentInter = interaction
    button_view.users = users
    button_view.guilds = guilds    
    button_view.bypass = bypass

    await interaction.response.send_message(message,view=button_view)

@d.tree.command()
async def heal(interaction: discord.Interaction, amount: int, selfheal: bool=False, name: str=""):
    """
    Assign healing.
    
    Parameters
    ----------
    amount: int
        Amount of damage to heal.
    selfheal: bool
        Whether or not the healing should be applied to self. If not, creates a button. Default: False
    name: str
        Name of the entity giving healing. (Optional)
    """
    #Set up some variables
    global users,guilds
    message = ""

    amount = abs(amount)
    if amount <= 0: #You said explicitly to adjust by 0? why would you do that
        await interaction.response.send_message("'"+str(amount)+" healing'? Very funny.",ephemeral=True)
        return 1
    if name != "":
        message = name+" gives "
    message += str(amount)+" HP of healing!"
    if selfheal:
        message = message[:-1]+" to you!"
   
    token = d.retrieveMcToken(str(interaction.guild_id),interaction.user.id,guilds,users)

    button_view = d.takeHealing()
    button_view.message = message 
    button_view.damage = amount
    button_view.parentInter = interaction
    button_view.users = users
    button_view.guilds = guilds    

    if selfheal:        
        retrieve = [d.statlayoutdict["currenthp"],
                d.statlayoutdict["hpmax"],
                ]
        current,maxhp=d.sheet.values().batchGet(spreadsheetId=token,ranges=retrieve).execute()['valueRanges']
        #Get values 
        maxhp = int(maxhp['values'][0][0])
        try: 
            current = int(current['values'][0][0])    
        except KeyError: #if current hp is missing, assume it's full.
            #Yes, this behavior differs from the levelup function
            #Because in combat if I assume they have no HP they'd be dead!
            current = maxhp
        current += amount
        current = min(current,maxhp) #overheals not allowed
        d.sheet.values().update(spreadsheetId=token,range=d.statlayoutdict["currenthp"],valueInputOption="USER_ENTERED",body={'values':[[current]]}).execute()
        await interaction.response.send_message(message,ephemeral=True) 
    else:
        await interaction.response.send_message(message,view=button_view)

@d.tree.command()
async def end_encounter(interaction: discord.Interaction, pips: int=0):
    """
    [GM Command] End the current encounter, giving players the opportunity to claim pips and level up.

    Parameters
    ----------
    pips: int
        The number of pips to grant for the encounter. (Default: 0)
    """
    global users,guilds

    message = "Encounter won! You've earned **"+str(pips)+"** experience pip(s). Click below to claim pips and then run: ```/levelup```"

    button_view = d.endEncounter()
    button_view.message = message
    button_view.pips = pips
    button_view.parentInter = interaction
    button_view.users = users
    button_view.guilds = guilds

    await interaction.response.send_message(message,view=button_view)

@d.tree.command()
async def request(interaction: discord.Interaction, modifier: str, goal: int, message: str="", exp: bool=True):
    """
    [GM Command] Request the specified roll from players.

    Parameters
    ----------
    modifier: str
        A modifier, following `/roll` syntax, for the roll.
    goal: int
        Value to meet or exceed when rolling. This is not relayed in the resulting message.
    message: str
        The message for the roll, to help players know what the roll is for. (Optional)
    exp: bool
        Automatically grant exp for attempting the roll, if applicable. (Default: True)
    """
    global users,guilds

    if message != "":
        message = "> "+message+"\n"
    message += "Requested roll: **"+modifier+"**"

    button_view = d.requestRoll()
    button_view.message = message
    button_view.mod = modifier
    button_view.guilds = guilds
    button_view.users = users
    button_view.goal = goal
    button_view.auto = autoexp

    await interaction.response.send_message(message,view=button_view)
