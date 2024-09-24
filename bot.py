import discord
from discord.ext import commands
from tokenn import tokenn
from discord.ui import Button, View
import os
from flask import Flask, request, jsonify
import threading
import asyncio

TRANSCRIPT_CHANNEL_ID = 1288232709608706078
TRANSCRIPT_FILE_NAME = 'ticket_transcript.txt'

# Setup Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    try:
        command_count = len(bot.commands)
        print('Bot Online')
        channel = bot.get_channel(1241145266447581325)
        await channel.send(":white_check_mark: **BOT ONLINE** \n **TUTTO LO STAFF SI SCUSA DEL DISAGIO MOMENTANEO** \n||<@&1267843450695581707>||")
        print(f'Comandi sincronizzati: {command_count}')
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='WebSiteInnovation'))
    except Exception as e:
        print(f'Errore durante la sincronizzazione dei comandi: {e}')

class CloseButton(discord.ui.View):
    def __init__(self, channel):
        super().__init__()
        self.channel = channel

    @discord.ui.button(label='Chiudi', style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.response.send_message('Il ticket è in fase di chiusura, per favore aspetta...', ephemeral=True)

            messages = []
            async for message in self.channel.history(limit=1000):
                messages.append(message)

            with open(TRANSCRIPT_FILE_NAME, 'w', encoding='utf-8') as f:
                for msg in messages:
                    f.write(f"{msg.author}: {msg.content}\n")

            transcript_channel = self.channel.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
            if transcript_channel is None:
                print("Canale di trascrizione non trovato.")
                return

            with open(TRANSCRIPT_FILE_NAME, 'rb') as f:
                await transcript_channel.send(file=discord.File(f, TRANSCRIPT_FILE_NAME))

            os.remove(TRANSCRIPT_FILE_NAME)
            await self.channel.delete()
            print(f'Ticket {self.channel.name} chiuso e trascritto con successo.')
        except Exception as e:
            print(f"Errore nella chiusura del ticket: {str(e)}")


class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Nessun timeout, la view sarà permanente fino alla cancellazione manuale

    @discord.ui.button(label='Supporto', style=discord.ButtonStyle.green)
    async def Supporto(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, 'supporto', 1276113395292307487, 1275921094490066954,
                                 'Benvenuto {member.mention} \n Attendi uno staffer, nel frattempo inizia a esporci la tua problematica.')

    @discord.ui.button(label='High', style=discord.ButtonStyle.red)
    async def High(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, 'High', 1288231730406232126, 1275946885932126229,
                                 'Benvenuto {member.mention} \n Attendi un alto grado ti risponderà subito.')

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str, category_id: int, role_id: int, welcome_message: str):
        try:
            member = interaction.user
            guild = interaction.guild
            if guild is None:
                await interaction.response.send_message("Guild non trovata.", ephemeral=True)
                return

            category = discord.utils.get(guild.categories, id=category_id)
            if category is None:
                await interaction.response.send_message("Categoria specificata non trovata.", ephemeral=True)
                return

            role = guild.get_role(role_id)
            if role is None:
                await interaction.response.send_message("Ruolo specificato non trovato.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                member: discord.PermissionOverwrite(read_messages=True),
                role: discord.PermissionOverwrite(read_messages=True)
            }
            ticket_channel = await guild.create_text_channel(name=f'ticket-{member.name}', category=category, overwrites=overwrites)

            welcome_view = CloseButton(channel=ticket_channel)
            await ticket_channel.send(content=f"|| <@&{role_id}> ||")
            await ticket_channel.send(content=welcome_message.format(member=member), view=welcome_view)
            await interaction.response.send_message(f'Ticket {ticket_type.capitalize()} aperto: {ticket_channel.mention}', ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"Errore nella creazione del ticket: {str(e)}", ephemeral=True)
            print(f"Errore nella creazione del ticket: {str(e)}")

@bot.command(name='Ticket', description='Crea un pannello ticket')
async def Ticket(ctx: commands.Context):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Non hai i permessi sufficienti per utilizzare questo comando.")
        return

    await recreate_ticket_panel(ctx)

async def recreate_ticket_panel(ctx):
    while True:
        try:
            # Cancella l'ultimo messaggio del pannello (se esiste)
            async for message in ctx.channel.history(limit=10):
                if message.author == ctx.me and len(message.components) > 0:
                    await message.delete()

            # Ricrea il pannello dei ticket
            view = Confirm()
            await ctx.send(
                'Per aprire un ticket, clicca qui \n'
                'Supporto: per richiedere supporto riguardante candidatura a staff o problemi con il sito \n'
                'High Staff: Richiedere supporto da parte degli alti gradi \n'
                '**VIETATO APRIRE TICKET A CASO PENA: WARN**',
                view=view
            )
        except Exception as e:
            print(f"Errore nel ricreare il pannello: {str(e)}")

        # Aspetta 10 minuti prima di ricreare il pannello
        await asyncio.sleep(600)

@bot.command(name='Close', description='Elimina il canale con trascrizione.')
async def Close(ctx: commands.Context):
    # Controlla se il nome del canale inizia con "Ticket"
    if not ctx.channel.name.startswith("ticket"):
        await ctx.send("Questo comando può essere utilizzato solo nei canali che iniziano con 'Ticket'.")
        return

    # Verifica se l'utente ha il permesso di gestire i canali
    if not ctx.author.guild_permissions.manage_channels:
        await ctx.send("Non hai i permessi sufficienti per eliminare questo canale.")
        return

    await ctx.send("Il ticket è in fase di chiusura, per favore aspetta...")

    try:
        # Recupera i messaggi del canale e crea il file di trascrizione
        messages = []
        async for message in ctx.channel.history(limit=1000):
            messages.append(message)

        with open(TRANSCRIPT_FILE_NAME, 'w', encoding='utf-8') as f:
            for msg in messages:
                f.write(f"{msg.created_at} - {msg.author}: {msg.content}\n")

        # Ottieni il canale di trascrizione
        transcript_channel = ctx.guild.get_channel(TRANSCRIPT_CHANNEL_ID)
        if transcript_channel is None:
            await ctx.send("Canale di trascrizione non trovato.")
            return

        # Invia il file di trascrizione al canale specificato
        with open(TRANSCRIPT_FILE_NAME, 'rb') as f:
            await transcript_channel.send(file=discord.File(f, TRANSCRIPT_FILE_NAME))

        # Rimuovi il file di trascrizione dopo averlo inviato
        os.remove(TRANSCRIPT_FILE_NAME)

        # Elimina il canale
        await ctx.channel.delete()
        print(f'Ticket {ctx.channel.name} chiuso e trascritto con successo.')

    except Exception as e:
        await ctx.send(f"Si è verificato un errore durante la chiusura del ticket: {str(e)}")
        print(f"Errore nella chiusura del ticket: {str(e)}")

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    bot.run(tokenn)