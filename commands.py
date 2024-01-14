#Imports
import discord, re
import numpy as np

#Setup
client = discord.Client(intents=discord.Intents.none())
tree = discord.app_commands.CommandTree(client)

#Comands

#List of commands. Important!
@tree.command(
    name="help",
    description="Lists available commands",
)
async def help(interaction: discord.Interaction):
    message = """**help** - Prints this help menu.
**roll** - Rolls a die, default 1d20, see command for options."""
    await interaction.response.send_message(message,ephemeral=True)

#Basic die rolls.
@tree.command(
    name="roll",
    description="Default: rolls 1d20. Rolls a number of dice with minimum, maximum, and modifier."
)
@discord.app_commands.describe(
    dice="String representing the dice rolled, in format `XdY+Z`, `XdY-Z`, or `XdY`.",
    goal="Value to meet or exceed.",
    private="Hide roll from other users"
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

