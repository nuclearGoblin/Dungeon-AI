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
async def roll(interaction: discord.Interaction, modifier: str="", goal: int=None, autoexp: bool=False, private: bool=False):
    """
    Rolls 1d20 with provided modifiers. Default modifier: 0.

    Parameters
    modifier: str
        String representing modifier, in format `X+skill+stat+Y`. (Default: 0. Example: `coolness+charisma+8`)
        Calls your default character if non-numeric values are provided.
    goal: int
        Value to meet or exceed when rolling. Reports back success/failure if given. (Optional)
    autoexp: bool
        Automatically grant exp for the roll, if applicable.
    private: bool
        Hide your roll and result from other users. (Default: False)
    ----------
    """
    button_view = None #unless defined
    global users,guilds
    rollname = "Rolling `1d20"
    mod = 0 #"mod" is the numeric modifier. "modifier" is the string we are parsing.
    if modifier != "":
        modifier = modifier.lower() #set case to all lower to prevent case-sensitivity
        modifier = "".join(modifier.split()) #strip all extra whitespace.
        rollname = rollname+"+"+modifier
        if not re.search(r"\b[+-]?((\d+)|([a-z]\w*))?([+-]((\d+)|([a-z]\w*)))*$",modifier):
            await interaction.response.send_message(
                "`modifier` argument format not recognized. "
                + "Please follow the format `skillname+statname+X`,"
                + "ex `coolness+charisma-13`.",ephemeral=True)
            return 1
        #Get modifier
        mode = [sym for sym in modifier if sym == "+" or sym == "-"]
        if modifier[0] not in  "+-": #If it's not going to be picked up here,
            mode.insert(0,"+")  #Then it was a positive value and should be added."
        if re.search("[+-]",modifier):
            print("presplit",modifier)
            modifier=re.split("[+-]",modifier)
            print("postsplit",modifier)
        if type(modifier) is not list:
            modifier = [modifier] #if modifier is a single value, make it a one-item list
        token = d.retrieveMcToken(str(interaction.guild.id),interaction.user.id,guilds,users)
        for i,entry in enumerate(modifier):
            if entry.isdigit(): #If the value is a number,
                mod += d.signed(int(entry),mode[i])
            else: #Should I make this a function since I'm gonna copy-paste it?
                modalias = d.check_alias(entry)
                #print("entry",entry,"had alias",modalias,"which has type",type(modalias))
                if type(modalias) is str: #if the entry has an alias,
                    toadd = d.retrievevalue(d.statlayoutdict[modalias],token)
                elif token is None: #assume we're looking for a skill, but we don't have a character
                    await interaction.response.send_message(
                            "You appear to have selected a skill name, "
                            + "but you have no default character sheet for me to check. "
                            + "Please either set a default character sheet using /link "
                            + "or double-check your roll syntax.",ephemeral=True)

                else: #assume it's a skill
                    print(token)
                    toadd,skillrow = d.getSkillInfo(entry,token)
                    rank = toadd
                    skillname = entry
                if toadd == "HTTP_ERROR":
                    mod = "HTTP_ERROR"
                    break #Stop calculating it and tell them to do it themselves.
                else: 
                    mod += d.signed(int(toadd),mode[i])
            
    #Generate a result
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
            if result >= goal: rollname += " (Success!)"
            else: rollname += " (Failure...)"
    rollname = rollname+"**." #end bold
    try: #If a skill was rolled, we will look at experience.
        skillname
        if not d.readonlytest(token):
            if autoexp: #automatically add to sheet
                expmsg = d.giveExp(skillrow,rank,token,skillname)
                rollname += " "+expmsg 
            else:
                button_view = d.expButton() #pass values to button class
                button_view.token = token
                button_view.skillrow = skillrow
                button_view.skillrank = rank
                button_view.skillname = skillname
                #view.message = rollname+" "
                button_view.parentInter = interaction
        else:
            rollname += " Don't forget to update your skill experience."
    except UnboundLocalError: #skillname is undefined, so we weren't rolling a skill
        pass
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
        token = url.split("/") #Now split along slashes.
        token = token[5] #Take the third entry
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
        gIDs = [int(x) for x in gIDs]
        mcIDs = d.strtolist(gRow.iloc[0]["mainCharIDs"])
        roArray = d.strtolist(uRow.iloc[0]["readonly"])
    
    #Test read the character sheet.
    try:
        name = d.retrievevalue(location=d.statlayoutdict["name"],token=token)
    except googleapiclient.errors.HttpError:
        await interaction.response.send_message(
            "Unable to reach character sheet. Please make sure that it is either public or shared with the bot, whose email is: `"
            +d.botmail+"`. If you provided a complete url, try providing only the token."
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
            print(gAssoc[pos])
            gAssoc[pos] = [int(x) for x in gAssoc[pos]]
        if ((guildID in gAssoc[pos] and not allguilds) or (gAssoc[pos] == "all" and allguilds)) and readonly == (roArray[pos] == "True"):
            #print("checking default",mcIDs[gIDs.index(guildID)],default,token in mcIDs[gIDs.index(guildID)])
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
        print(type(guildID))
        gIDs.append(guildID)
        print(gIDs)
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
        except IndexError:
            mcIDs.append(None)
            if len(mcIDs) < gIDs.index(guildID): #If we still don't have that many indices,
                raise ValueError("Your character database is corrupted. Please copy down the information you can with `/view char:all`, clear your database with `/unlink char:all`, and recreate it. Please also [submit a bug report on our GitHub](https://github.com/nuclearGoblin/Dungeon-AI).")
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
        uRow.at[0,"guildAssociations"] = str(gAssoc)
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
    #Reformat data as necessary
    uRow.at[0,"guildAssociations"] = str(uRow.iloc[0]["guildAssociations"])
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
        guilds.loc[guilds['userID'] == interaction.user.id] = gRow
        users.loc[users['userID'] == interaction.user.id] = uRow
        users.to_sql(name='users',con=d.connection,if_exists="replace")
        guilds.to_sql(name='guilds',con=d.connection,if_exists="replace")
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
            gAssoc = d.strtolist(uRow.iloc[0]["guildAssociations"])[pos]
            if type(gAssoc) == str: gAssoc = [gAssoc]
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
            row[2] = str(mcIDs[gIDs.index(guildID)] == character)
        except ValueError: #If it's not associated with this guild
            row[2] = "N/A"
        gAssoc = d.strtolist(uRow.iloc[0]["guildAssociations"])[pos]
        if type(gAssoc) == str: 
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
    if False: #non-commitally removing this, as I want to restructure.
        if char == "all":
            #delete everything
            users = users[users["userID"] != interaction.user.id]
            guilds = guilds[guilds["userID"] != interaction.user.id]
            users.to_sql(name='users',con=d.connection,if_exists="replace")
            guilds.to_sql(name='guilds',con=d.connection,if_exists="replace")
            await interaction.response.send_message("All of your user data was deleted from the bot's database.",ephemeral=True)
            #Reload edited databases.
            users = pd.read_sql("SELECT "+", ".join(d.userCols)+" FROM users",d.connection,dtype=d.types)
            guilds = pd.read_sql("SELECT "+", ".join(d.guildCols)+" FROM guilds",d.connection,dtype=d.types)
            return
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
        #gIDs.pop(gloc); mcIDs.pop(gloc) #Do this at guild collection.
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
                    await interaction.response.send_message("There is no character data associated with the guild",guildID)
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
        if emptyguilds>1: message += "s no longer have"
        else: message += " no longer has"
        message += " linked characters after this."
    if userdel:
        message += " This action resulted in the removal of all of your user data."
    await interaction.response.send_message(message,ephemeral=True)

#Other commands to write:
#verify (check the read/writability of a character sheet and update the db entry if necessary)
# - this is a feature I see other functions using so make it its own function
#skillroll (roll the associated skill+modifiers, this is the main function we want)
# - functions within this will be called by skillroll
#requestroll (be able to request players click a button and roll a thing.)
#configure (bot settings per server, maybe uses a third table, things like who can view sheets and request rolls.)
