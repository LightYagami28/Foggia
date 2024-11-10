import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from tokenn import tokenn
from flask import Flask, jsonify
import os
import threading
import asyncio

TRANSCRIPT_CHANNEL_ID = 1288232709608706078
TRANSCRIPT_FILE_NAME = 'ticket_transcript.txt'

# Setup Flask
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"status": "Bot is running!"})

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# Define bot with all intents enabled
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    try:
        channel = bot.get_channel(1241145266447581325)
        await channel.send(":white_check_mark: **BOT ONLINE** \n **TUTTO LO STAFF SI SCUSA DEL DISAGIO MOMENTANEO** \n||<@&1267843450695581707>||")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='WebSiteInnovation'))
        print(f'Bot Online | Comandi sincronizzati: {len(bot.commands)}')
    except Exception as e:
        print(f'Errore durante l\'inizializzazione: {e}')

class CloseButton(View):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    @discord.ui.button(label='Chiudi', style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.close_ticket(interaction)

    async def close_ticket(self, interaction):
        await interaction.response.send_message('Chiusura del ticket in corso, attendere...', ephemeral=True)
        try:
            messages = [msg async for msg in self.channel.history(limit=1000)]
            with open(TRANSCRIPT_FILE_NAME, 'w', encoding='utf-8') as f:
                f.writelines([f"{msg.author}: {msg.content}\n" for msg in messages])

            transcript_channel = self.channel.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
            if transcript_channel:
                with open(TRANSCRIPT_FILE_NAME, 'rb') as f:
                    await transcript_channel.send(file=discord.File(f, TRANSCRIPT_FILE_NAME))
            os.remove(TRANSCRIPT_FILE_NAME)
            await self.channel.delete()
            print(f'Ticket {self.channel.name} chiuso e trascritto.')
        except Exception as e:
            print(f"Errore chiusura ticket: {e}")

class Confirm(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Supporto', style=discord.ButtonStyle.green)
    async def Supporto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, 'supporto', 1276113395292307487, 1275921094490066954, 'Benvenuto {member.mention} \n Attendi uno staffer.')

    @discord.ui.button(label='High', style=discord.ButtonStyle.red)
    async def High(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, 'High', 1288231730406232126, 1275946885932126229, 'Benvenuto {member.mention} \n Attendi un alto grado.')

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str, category_id: int, role_id: int, welcome_message: str):
        try:
            member = interaction.user
            guild = interaction.guild
            category = discord.utils.get(guild.categories, id=category_id)
            role = guild.get_role(role_id)

            if not category or not role:
                await interaction.response.send_message("Categoria o ruolo non trovati.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                member: discord.PermissionOverwrite(read_messages=True),
                role: discord.PermissionOverwrite(read_messages=True)
            }
            ticket_channel = await guild.create_text_channel(f'ticket-{member.name}', category=category, overwrites=overwrites)
            welcome_view = CloseButton(channel=ticket_channel)
            await ticket_channel.send(content=f"|| <@&{role_id}> || {welcome_message.format(member=member)}", view=welcome_view)
            await interaction.response.send_message(f'Ticket {ticket_type.capitalize()} aperto: {ticket_channel.mention}', ephemeral=True)
        except Exception as e:
            print(f"Errore nella creazione del ticket: {e}")

@bot.command(name='Ticket', description='Crea un pannello ticket')
async def Ticket(ctx: commands.Context):
    if ctx.author.guild_permissions.administrator:
        await ctx.send(
            'Per aprire un ticket, clicca qui\n'
            'Supporto: per supporto candidature o problemi\n'
            'High Staff: supporto da parte degli alti gradi\n'
            '**VIETATO APRIRE TICKET A CASO**',
            view=Confirm()
        )

@bot.command(name='Close', description='Elimina il canale con trascrizione.')
async def Close(ctx: commands.Context):
    if ctx.channel.name.startswith("ticket") and ctx.author.guild_permissions.manage_channels:
        await ctx.send("Il ticket è in fase di chiusura, per favore aspetta...")
        try:
            messages = [msg async for msg in ctx.channel.history(limit=1000)]
            with open(TRANSCRIPT_FILE_NAME, 'w', encoding='utf-8') as f:
                f.writelines([f"{msg.created_at} - {msg.author}: {msg.content}\n" for msg in messages])

            transcript_channel = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
            if transcript_channel:
                with open(TRANSCRIPT_FILE_NAME, 'rb') as f:
                    await transcript_channel.send(file=discord.File(f, TRANSCRIPT_FILE_NAME))
            os.remove(TRANSCRIPT_FILE_NAME)
            await ctx.channel.delete()
            print(f'Ticket {ctx.channel.name} chiuso e trascritto.')
        except Exception as e:
            print(f"Errore chiusura ticket: {e}")
    else:
        await ctx.send("Permessi insufficienti o canale non valido.")

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(tokenn)
