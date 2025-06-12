import discord, sys
sys.path.append('./')
import decs as d

class Mob():
    def __init__(self):
        #Things to be defined in the monster itself
        self.hp = 0
        self.mp = 0
        self.evasion = 0
        self.mobtype = "enemy"
        self.classification = ""
        self.name = ""
        self.text = ""
        self.attacks = [{"name":"","mod":0,"damage":0}]
        self.perfloor = 0

class MobAttackButtons(discord.ui.View,Mob):
    def __init__(self):
        super().__init__()

        self.embed = discord.Embed()
        self.passing = []
        self.responding = []
        #To pass in
        self.parentInter = discord.Interaction 
        self.message = ""

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
        if interaction.user in self.passing:
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

    @discord.ui.button(label="Roll",style=discord.ButtonStyle.primary,disabled=True)
    async def roll_button(self, interaction: discord.Interaction, button:discord.ui.Button):
        if interaction.user != self.parentInter.user:
            pass #If a player tries to roll, do nothing.
        else:
            for child in self.children: #Once this is pressed, disable the buttons.
                if type(child) is discord.ui.Button:
                    child.disabled = True
        await interaction.response.defer()
