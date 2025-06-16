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
        self.attacks = [{"name":"","mod":0,"damage":0}]
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
type = ['Enemy','NPC','Elite','Crawler','Pet','Boss','Minion','God','Corpse']

#A small function that finds mob by name
def get_mob(mob: str):
    return [x for x in MOBS if x.name.lower().strip() == mob.lower().strip()]

#Here's where all the magic happens babey!
class MobAttackButtons(discord.ui.View,Mob):
    def __init__(self,parentInter):
        super().__init__()

        self.embed = discord.Embed()
        self.passing = []
        self.responding = []
        #To pass in
        self.parentInter = parentInter 
        self.message = ""
        self.guilds = None
        self.users = None
        self.attack = ""
        self.mob = ""

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
            self.responding.remove(interaction.user)

            d.reconstruct_response_lists(self.embed,self.responding,self.passing)
            await self.parentInter.edit_original_response(content=self.message,view=self,embed=self.embed)
        await interaction.response.defer()

    #The roll button for the GM
    @discord.ui.button(label="Roll",style=discord.ButtonStyle.primary,disabled=True)
    async def roll_button(self, interaction: discord.Interaction, button:discord.ui.Button):
        if interaction.user != self.parentInter.user:
            pass #If a player tries to roll, do nothing.
        else: #If the GM rolls,
            for child in self.children: #Once this is pressed, disable the buttons.
                if type(child) is discord.ui.Button:
                    child.disabled = True
            #Get mob information
            mob_inst = get_mob(self.mob)
            if mob_inst == []: #If the mob doesn't exist, give up and report failure
                await self.parentInter.edit_original_response(content="Mob `"+self.mob+"` not found.",embed=mobs)
                await interaction.response.defer()
                return 1
            attack_inst = get_mob(self.mob).attacks
            if self.attack == "": #If not specified, default to the first.
                attack_inst = attack_inst[0]
            else: #If specified,
                try: #first see if it's positional.
                    attack_inst = attack_inst[int(self.attack)]
                except ValueError: #If you can't call it as a position,
                    #Look the attack up by name
                    attack_inst = [x for x in attack_inst if x['name'].lower().strip() == self.attack.lower().strip()][0]
                    #If you didn't find anything,
                    if attack_inst == []: #Give up and report the failure.
                        await self.parentInter.edit_original_response(content="Attack `"+self.attack+"` for creature `"+self.mob+"` not found.",embed=desc(mob_inst[0]))
                        await interaction.response.defer()
                        return 2
            #Now that we know the attack, we can roll it.
            result = np.random.randint(1,20) + attack_inst['mod']
            #Get defender info
            players = self.passing + self.responding
            evasions = []
            hits = []
            for player in players:
                token = d.retrieveMcToken(str(interaction.guild_id),player.id,self.guilds,self.users)
                evasion = d.retrievevalue(token,d.statlayoutdict['Evasion'])
                evasions.append(evasion)
                if evasion < result:
                    hits.append(player)
                    if player in self.passing:
                        pass 
            
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
runenote.attacks[0] = {'name':"Sing",'mod':0,'damage':4}
runenote.flavor = "Runesong"

# A list of all creatures, for utility of other fucntions
mobs = discord.Embed(title="Bestiary",url="https://docs.google.com/document/d/14qkOLhg9iDBqj0Go3g6nb2oTCQBHuCwg3gOzaIzFHFE")
namelist = [mob.name for mob in MOBS]
namelist.sort() #Alphabetize the list
for mob in namelist:
    mobs.add_field(name=mob,value="")
