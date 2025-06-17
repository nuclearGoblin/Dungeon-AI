import discord
import numpy as np
import decs as d

#Self-updating list of all creatures
MOBS = []

#structure
class Mob():
    def __init__(self,name):
        #Things to be defined in the monster itself
        self.name = name
        self.hp = 0
        self.mp = 0
        self.evasion = 0
        self.mobtype = "Enemy"
        self.classification = ""
        self.text = ""
        self.attacks = [{"name":"","mod":0,"damage":0,"bypass":False}] #bypass: bypass dr or no
        self.perfloor = 0
        self.image = ""
        self.flavor = ""
        MOBS.append(self)

#All the valid classifications and their colors
classifications = {
        "Elf":0x92A692,
        "Goblin":0x394E2A,
        "Fairy":0x2496F2,
        "Orc":0x4B5A4C,
        "Human":0xFABF2E,
        "Lizard":0x8BC34A,
        "Bird":0x2196F3,
        "Canine":0x867977,
        "Feline":0xFF6F00,
        "Slime":0xA4D5A6,
        "Undead":0xFBF9EB,
        "Insect":0x449346,
        "Rodent":0x7E645B,
        "Elemental":0xD44316,
        "Machine":0xAEBCC3,
        "Plant":0x00FF00,
        "Construct":0xECEFF1,
        "Dwarf":0xF9A825,
        "Gnome":0x4DB6AC,
        "Caprini":0xBCAAA4,
        "Abomination":0xDAE575,
        "Aquatic":0x0000FF
        }

#All the valid types
types = ['Enemy','NPC','Elite','Crawler','Pet','Boss','Minion','God','Corpse']

#A small function that finds mob by name
def get_mob(mob: str):
    return [x for x in MOBS if x.name.lower().strip() == mob.lower().strip()]

#Here's where all the magic happens babey!
class MobAttackButtons(discord.ui.View,Mob):
    def __init__(self,parentInter):
        super().__init__()

        self.embed = discord.Embed() #For initial message
        self.passing = []
        self.responding = []
        self.drs = []
        self.names = []
        self.maxhps = []
        self.hps = []
        self.tokens = []
        #To pass in
        self.parentInter = parentInter 
        self.message = ""
        self.guilds = None
        self.users = None
        self.attack = ""
        self.mob = ""
        self.attack_inst = {}

        self.embed.add_field(name="Responding",value="")
        self.embed.add_field(name="Passed",value="",inline=False)

    @discord.ui.button(label="Respond",style=discord.ButtonStyle.success)
    async def respond_button(self, interaction: discord.Interaction, button:discord.ui.Button):
        if interaction.user in self.responding: #Nothing to do
            pass
        elif interaction.user != self.parentInter.user:
            for child in self.children: #Can't roll until done!
                if (type(child) is discord.ui.Button) and child.label == "Roll":
                    child.disabled = False
            if interaction.user in self.passing: #Remove from other list if applicable
                self.passing.remove(interaction.user)
            self.responding.append(interaction.user)
            d.reconstruct_response_lists(self.embed,self.responding,self.passing)
            await self.parentInter.edit_original_response(content=self.message,view=self,embed=self.embed)
        await interaction.response.defer()

    @discord.ui.button(label="Pass",style=discord.ButtonStyle.secondary)
    async def pass_button(self, interaction: discord.Interaction, button:discord.ui.Button):
        if interaction.user in self.passing: #Nothing to do here
            pass
        elif interaction.user != self.parentInter.user:
            for child in self.children:
                if (type(child) is discord.ui.Button) and child.label == "Roll":
                    child.disabled = False
            self.passing.append(interaction.user)
            if interaction.user in self.responding: #Remove from other list if applicable.
                self.responding.remove(interaction.user)

            d.reconstruct_response_lists(self.embed,self.responding,self.passing)
            await self.parentInter.edit_original_response(content=self.message,view=self,embed=self.embed)
        await interaction.response.defer()

    #The roll button for the GM #############3
    @discord.ui.button(label="Roll",style=discord.ButtonStyle.primary,disabled=True)
    async def roll_button(self, interaction: discord.Interaction, button:discord.ui.Button):
        if interaction.user != self.parentInter.user:
            pass #If a player tries to roll, do nothing.
        else: #If the GM rolls,
            damage_button = d.takeDamage(interaction) #replace the buttons with a damage button
            damage_button.clickedby = [0] #set up a dummy entry to prevent positioning issues
            #Get mob information
            #Now that we know the attack, we can roll it.
            result = np.random.randint(1,20) + self.attack_inst['mod']
            #We also know the appropriate damage amount.
            damage_button.damage = self.attack_inst['damage']
            #Get defender info
            players = self.passing + self.responding
            hits = []
            evasions = []
            for player in players: #For each player,
                #Get the token,
                token = d.retrieveMcToken(str(interaction.guild_id),player.id,self.guilds,self.users)
                self.tokens.append(token)
                #Find their evasion
                dr,current,maxhp,name,evasion = d.getHpForEmbed(token)
                self.drs.append(dr)
                self.hps.append(current)
                self.maxhps.append(maxhp)
                self.names.append(name)
                evasions.append(evasion) #Track this for reporting later
                if evasion < result: #If they were hit,
                    hits.append(player) #Write that down
                    if player in self.passing: #If they passed, deal damage automatically
                        damage_button.clickedby.append(player)
            #Generate message describing who got hit
            damage_button.embeds.append(discord.Embed(title=self.attack_inst['name'],
                                                      colour=d.hp_color(1-len(hits)/len(players)),description=str(self.attack_inst['damage'])+" damage")) 
            hitstext = "" #Initialize strings to fill
            misstext = ""
            for i,player in enumerate(players):
                if player in hits:
                    if player in self.passing:
                        #Finish processing player damage
                        hitstext += "**"+self.names[i]+"** ("+player.mention+", Evasion "+str(evasions[i])+"), "
                        #Calculate damage to deal
                        damage = self.attack_inst['damage']
                        if not self.attack_inst['bypass']: #Ssubtract dr from damage, to a minimum of 0
                            print(self.drs[i])
                            damage -= self.drs[i]
                            damage = max(damage,0)
                        #Subtract damage from hp
                        self.hps[i] -= damage
                        self.hps[i] = max(0,self.hps[i]) #hp below 0 is game over -- dead is dead!
                        d.sheet.values().update(spreadsheetId=self.tokens[i],range=d.statlayoutdict["currenthp"],valueInputOption="USER_ENTERED",body={'values':[[self.hps[i]]]}).execute()
                        #And report back that this was already done
                        damage_button.embeds.append(discord.Embed(title=self.names[i],description=interaction.user.mention,colour=d.hp_color(self.hps[i]/self.maxhps[i])))
                        damage_button.embeds[-1].add_field(name="Taken",value=damage)
                        damage_button.embeds[-1].set_footer(text="Remaining "+str(self.hps[i])+"/"+str(self.maxhps[i]))

                    else: #If player didn't pass, don't do anything for them -- may have missed
                        hitstext += self.names[i]+" ("+player.mention+", Evasion "+str(evasions[i])+"), "
                else: #If the player was missed,
                    misstext += self.names[i]+" ("+player.mention+", Evasion "+str(evasions[i])+"), "
            damage_button.embeds[0].set_author(name=self.mob.capitalize())
            damage_button.embeds[0].set_footer(text="Rolled: "+str(result),icon_url="https://static.vecteezy.com/system/resources/previews/020/910/995/non_2x/dice-d20-icon-design-free-vector.jpg")
            damage_button.embeds[0].add_field(name="Hit",inline=False,value=hitstext[:-2])
            damage_button.embeds[0].add_field(name="Missed",inline=False,value=misstext[:-2])
            #Pass in other necessary values
            damage_button.damage = self.attack_inst['damage']
            damage_button.guilds = self.guilds
            damage_button.users = self.users
            damage_button.bypass = self.attack_inst['bypass']

            #And respond
            if hitstext == "": #If no one was hit, no damage button
                await self.parentInter.edit_original_response(content="",embed=damage_button.embeds[0],view=None)
            else:
                await self.parentInter.edit_original_response(content="",view=damage_button,embeds=damage_button.embeds)
        #And respond to button
        await interaction.response.defer()

#Return a bestiary page
def desc(creature: Mob):
    #name, special text, color from classification, and rules doc
    embed = discord.Embed(title=creature.name,description=creature.text,
                          colour=classifications[creature.classification],
                          url="https://docs.google.com/document/d/14qkOLhg9iDBqj0Go3g6nb2oTCQBHuCwg3gOzaIzFHFE")
    #Creature type and classification
    embed.set_author(name=creature.mobtype+", "+creature.classification)
    #Image, if exists
    if creature.image != "":
        embed.set_thumbnail(url=creature.image)
    #Max per floor
    embed.add_field(name="Per floor",value=creature.perfloor)
    #Flavor text
    embed.set_footer(text=creature.flavor) #maybe could set an icon from classification?
    #Combat stats
    embed.add_field(name="HP",value=creature.hp)
    embed.add_field(name="MP",value=creature.mp)
    embed.add_field(name="Evasion",value=creature.evasion)
    #Attacks
    for attack in creature.attacks:
        embed.add_field(name="Attack: "+attack['name'],inline=False,
                        value="+"+str(attack['mod'])+", "+str(attack['damage'])+" damage")
    #Alright boss let's ship it
    return embed

#############
# Creatures #
#############
#The individual monsters n stuff.

runenote = Mob("Runic Note")
runenote.classification = "Undead"
runenote.text = "Special rules text here"
runenote.attacks[0] = {'name':"Sing",'mod':10,'damage':4,'bypass':False}
runenote.attacks.append({'name':"Sing louder",'mod':5,'damage':2,'bypass':True})
runenote.flavor = "Runesong"

# A list of all creatures, for utility of other fucntions
mobs = discord.Embed(title="Bestiary",url="https://docs.google.com/document/d/14qkOLhg9iDBqj0Go3g6nb2oTCQBHuCwg3gOzaIzFHFE")
namelist = [mob.name for mob in MOBS]
namelist.sort() #Alphabetize the list
for mob in namelist:
    mobs.add_field(name=mob,value="")
