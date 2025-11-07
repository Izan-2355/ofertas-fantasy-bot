import discord
from discord import app_commands
from discord.ui import Select, View, Button
import os

# Configuración
TOKEN = os.getenv('DISCORD_TOKEN', 'MTQzNjI3OTQwMzA3OTI3NDU5Ng.GozFPG.ici1sNaqDYC5azmpZB08zkji2fhv5Ev-wPDZo4')
GUILD_ID = 1310024114312056832

# Contador de ofertas global
offer_counter = 1
active_offers = {}

# Configurar intents
intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f'✅ Bot conectado como {client.user}')
        print(f'✅ Comandos sincronizados en el servidor')
    except Exception as e:
        print(f'❌ Error al sincronizar comandos: {e}')

@tree.command(name="crear_oferta", description="Crea una nueva oferta de LaLiga Fantasy", guild=discord.Object(id=GUILD_ID))
async def crear_oferta(interaction: discord.Interaction):
    """Comando para crear una oferta"""
    global offer_counter
    
    # Obtener el rol Fantasy Manager
    fantasy_role = discord.utils.get(interaction.guild.roles, name="Fantasy Manager")
    
    if not fantasy_role:
        await interaction.response.send_message("❌ No se encontró el rol 'Fantasy Manager' en este servidor.", ephemeral=True)
        return
    
    # Obtener miembros con el rol Fantasy Manager (excluyendo al usuario actual)
    fantasy_members = [m for m in interaction.guild.members if fantasy_role in m.roles and m != interaction.user and not m.bot]
    
    if len(fantasy_members) == 0:
        await interaction.response.send_message("❌ No hay otros usuarios con el rol 'Fantasy Manager'.", ephemeral=True)
        return
    
    # Crear select menu con los usuarios
    class UserSelect(Select):
        def __init__(self):
            options = [
                discord.SelectOption(
                    label=member.display_name,
                    value=str(member.id),
                    description=f"Hacer oferta a {member.name}"
                )
                for member in fantasy_members[:25]  # Discord limita a 25 opciones
            ]
            super().__init__(placeholder="Selecciona un Fantasy Manager...", options=options, custom_id="user_selector")
        
        async def callback(self, interaction: discord.Interaction):
            global offer_counter
            
            target_id = int(self.values[0])
            target_member = interaction.guild.get_member(target_id)
            creator = interaction.user
            
            # Crear categoría
            category_name = f"Oferta - {offer_counter} - {creator.display_name}"
            
            # Permisos para la categoría
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                creator: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    speak=True,
                    connect=True,
                    read_message_history=True
                ),
                target_member: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    speak=True,
                    connect=True,
                    read_message_history=True
                ),
                fantasy_role: discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    speak=False,
                    connect=True,
                    read_message_history=True
                )
            }
            
            try:
                # Crear la categoría
                category = await interaction.guild.create_category(
                    name=category_name,
                    overwrites=overwrites
                )
                
                # Crear canal de voz
                voice_channel = await interaction.guild.create_voice_channel(
                    name=f"🎤 Oferta {offer_counter}",
                    category=category
                )
                
                # Crear canal de texto
                text_channel = await interaction.guild.create_text_channel(
                    name=f"💬 oferta-{offer_counter}",
                    category=category
                )
                
                # Guardar info de la oferta
                active_offers[category.id] = {
                    'number': offer_counter,
                    'creator': creator.id,
                    'target': target_member.id,
                    'participants': [creator.id, target_member.id],
                    'text_channel': text_channel.id,
                    'voice_channel': voice_channel.id,
                    'category': category.id
                }
                
                # Crear botones para el canal de texto
                class OfferButtons(View):
                    def __init__(self):
                        super().__init__(timeout=None)
                    
                    @discord.ui.button(label="Contraoferta", style=discord.ButtonStyle.primary, emoji="🔄", custom_id="contraoferta_btn")
                    async def contraoferta_button(self, interaction: discord.Interaction, button: Button):
                        offer_data = active_offers.get(interaction.channel.category.id)
                        if not offer_data:
                            await interaction.response.send_message("❌ Esta oferta ya no existe.", ephemeral=True)
                            return
                        
                        user_id = interaction.user.id
                        if user_id in offer_data['participants']:
                            await interaction.response.send_message("✅ Ya tienes permisos completos en esta oferta.", ephemeral=True)
                            return
                        
                        # Dar permisos completos al usuario
                        member = interaction.guild.get_member(user_id)
                        category = interaction.channel.category
                        
                        await category.set_permissions(
                            member,
                            view_channel=True,
                            send_messages=True,
                            speak=True,
                            connect=True,
                            read_message_history=True
                        )
                        
                        offer_data['participants'].append(user_id)
                        await interaction.response.send_message(f"✅ {member.mention} ahora puede participar activamente en la oferta.", ephemeral=False)
                    
                    @discord.ui.button(label="Cerrar", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="cerrar_btn")
                    async def cerrar_button(self, interaction: discord.Interaction, button: Button):
                        offer_data = active_offers.get(interaction.channel.category.id)
                        if not offer_data:
                            await interaction.response.send_message("❌ Esta oferta ya no existe.", ephemeral=True)
                            return
                        
                        # Solo el creador o el objetivo pueden cerrar
                        if interaction.user.id not in [offer_data['creator'], offer_data['target']]:
                            await interaction.response.send_message("❌ Solo los participantes principales pueden cerrar esta oferta.", ephemeral=True)
                            return
                        
                        await interaction.response.send_message("🔒 Cerrando oferta...", ephemeral=True)
                        
                        # Eliminar la categoría y todos sus canales
                        category = interaction.channel.category
                        for channel in category.channels:
                            await channel.delete()
                        await category.delete()
                        
                        # Eliminar del registro
                        del active_offers[category.id]
                
                # Enviar mensaje con botones al canal de texto
                embed = discord.Embed(
                    title=f"📋 Oferta #{offer_counter}",
                    description=f"**Creador:** {creator.mention}\n**Destinatario:** {target_member.mention}\n\n"
                                f"🔹 Usa el botón **Contraoferta** para participar activamente\n"
                                f"🔹 Usa el botón **Cerrar** para terminar la negociación\n\n"
                                f"⚠️ **Recordatorio:** Durante la negociación NO se puede pagar cláusula del jugador ofertado.",
                    color=discord.Color.blue()
                )
                
                await text_channel.send(embed=embed, view=OfferButtons())
                await text_channel.send(f"{creator.mention} {target_member.mention} - ¡La oferta ha sido creada!")
                
                await interaction.response.send_message(
                    f"✅ Oferta #{offer_counter} creada exitosamente!\n"
                    f"📁 Categoría: {category.mention}\n"
                    f"💬 Chat: {text_channel.mention}\n"
                    f"🎤 Voz: {voice_channel.mention}",
                    ephemeral=True
                )
                
                offer_counter += 1
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Error al crear la oferta: {str(e)}", ephemeral=True)
    
    view = View(timeout=None)
    view.add_item(UserSelect())
    
    await interaction.response.send_message(
        "👥 **Selecciona a quién quieres hacer la oferta:**",
        view=view,
        ephemeral=True
    )

# Ejecutar el bot
client.run(TOKEN)
