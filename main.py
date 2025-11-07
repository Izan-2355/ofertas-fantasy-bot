import discord
from discord import app_commands
from discord.ui import Select, View, Button
import os

# Configuración
TOKEN = os.getenv('DISCORD_TOKEN', 'MTQ2MjI3OTQwMzA3OTI3NDU5Ng.GozFPG.icils4mqDYCSazmgZB88zkji1zfhv5Ev-wPOZo4')
GUILD_ID = 1310024114312056832
OFERTAS_CHANNEL_ID = 1436265469966290976  # ID del canal #ofertas

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

# Vista persistente con el botón "Crear Oferta"
class PersistentOfferView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Sin timeout para que sea permanente
    
    @discord.ui.button(label="📩 Crear Oferta", style=discord.ButtonStyle.primary, custom_id="crear_oferta_button")
    async def crear_oferta_button(self, interaction: discord.Interaction, button: Button):
        await show_manager_selection(interaction)

# Función para mostrar el modal de selección
async def show_manager_selection(interaction: discord.Interaction):
    # Obtener rol Fantasy Manager
    guild = interaction.guild
    fantasy_role = discord.utils.get(guild.roles, name="Fantasy Manager")
    
    if not fantasy_role:
        await interaction.response.send_message("❌ No se encontró el rol Fantasy Manager", ephemeral=True)
        return
    
    # Filtrar miembros con el rol
    managers = [member for member in guild.members if fantasy_role in member.roles and not member.bot]
    
    if not managers:
        await interaction.response.send_message("❌ No hay Fantasy Managers disponibles", ephemeral=True)
        return
    
    # Crear el select menu
    select = Select(
        placeholder="Selecciona un Fantasy Manager...",
        options=[discord.SelectOption(label=member.display_name, value=str(member.id), description=f"Hacer oferta a {member.display_name}") for member in managers[:25]]  # Discord limita a 25 opciones
    )
    
    async def select_callback(select_interaction: discord.Interaction):
        target_id = int(select.values[0])
        target_member = guild.get_member(target_id)
        await create_offer(select_interaction, target_member)
    
    select.callback = select_callback
    view = View()
    view.add_item(select)
    
    await interaction.response.send_message("👤 Selecciona a quién quieres hacer la oferta:", view=view, ephemeral=True)

# Función para crear la oferta
async def create_offer(interaction: discord.Interaction, target_member: discord.Member):
    global offer_counter
    
    try:
        guild = interaction.guild
        creator = interaction.user
        
        # Nombre de la categoría
        category_name = f"Oferta - {offer_counter} - {creator.display_name}"
        
        # Obtener roles necesarios
        fantasy_role = discord.utils.get(guild.roles, name="Fantasy Manager")
        everyone_role = guild.default_role
        
        # Permisos para la categoría
        overwrites = {
            everyone_role: discord.PermissionOverwrite(view_channel=False),
            creator: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True
            ),
            target_member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                connect=True,
                speak=True
            ),
            fantasy_role: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                connect=True,
                speak=False
            )
        }
        
        # Crear categoría
        category = await guild.create_category(category_name, overwrites=overwrites)
        
        # Crear canal de voz
        voice_channel = await guild.create_voice_channel("🔊 Voz", category=category)
        
        # Crear canal de texto
        text_channel = await guild.create_text_channel("💬 Negociación", category=category)
        
        # Vista con botones para el canal de texto
        view = View(timeout=None)
        
        # Botón Contraoferta
        contraoferta_button = Button(label="🔄 Contraoferta", style=discord.ButtonStyle.secondary, custom_id=f"contraoferta_{offer_counter}")
        async def contraoferta_callback(button_interaction: discord.Interaction):
            if button_interaction.user != creator and button_interaction.user != target_member:
                await button_interaction.response.send_message("❌ Solo los participantes pueden usar este botón", ephemeral=True)
                return
            
            # Determinar quién hace la contraoferta
            if button_interaction.user == creator:
                new_target = target_member
            else:
                new_target = creator
            
            # Intercambiar permisos
            await text_channel.set_permissions(button_interaction.user, 
                view_channel=True, send_messages=True, read_message_history=True, connect=True, speak=True)
            await text_channel.set_permissions(new_target,
                view_channel=True, send_messages=True, read_message_history=True, connect=True, speak=True)
            
            await button_interaction.response.send_message(f"✅ {button_interaction.user.mention} ha hecho una contraoferta", ephemeral=False)
        
        contraoferta_button.callback = contraoferta_callback
        view.add_item(contraoferta_button)
        
        # Botón Cerrar
        cerrar_button = Button(label="🔒 Cerrar Oferta", style=discord.ButtonStyle.danger, custom_id=f"cerrar_{offer_counter}")
        async def cerrar_callback(button_interaction: discord.Interaction):
            if button_interaction.user != creator and button_interaction.user != target_member:
                await button_interaction.response.send_message("❌ Solo los participantes pueden cerrar la oferta", ephemeral=True)
                return
            
            await button_interaction.response.send_message(f"🔒 Oferta cerrada por {button_interaction.user.mention}. Eliminando canales...", ephemeral=False)
            
            # Eliminar categoría y canales
            for channel in category.channels:
                await channel.delete()
            await category.delete()
            
            # Eliminar de ofertas activas
            if offer_counter in active_offers:
                del active_offers[offer_counter]
        
        cerrar_button.callback = cerrar_callback
        view.add_item(cerrar_button)
        
        # Mensaje inicial en el canal de texto
        welcome_msg = f"""🤝 **NEGOCIACIÓN DE OFERTA #{offer_counter}**

**Participantes:**
• {creator.mention}
• {target_member.mention}

**📋 Normas de la negociación:**
⛔ NO se puede pagar la cláusula durante una negociación activa
✅ Tras finalizar, se puede hacer el clausulazo
⏰ Los clausulazos solo están permitidos hasta el **jueves a las 12:00**
🔒 El jugador cuya cláusula se negocia NO puede modificarla hasta que termine la jornada

**Botones disponibles:**
🔄 **Contraoferta** - Permite al otro participante responder
🔒 **Cerrar Oferta** - Finaliza y elimina esta negociación

¡Buena suerte! 🍀
        """
        
        await text_channel.send(welcome_msg, view=view)
        
        # Guardar oferta activa
        active_offers[offer_counter] = {
            'category': category.id,
            'creator': creator.id,
            'target': target_member.id
        }
        
        # Incrementar contador
        offer_counter += 1
        
        await interaction.response.send_message(f"✅ Oferta creada: {category.name}\n📂 Canales: {voice_channel.mention} y {text_channel.mention}", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error al crear la oferta: {e}", ephemeral=True)
        print(f"Error: {e}")

@client.event
async def on_ready():
    try:
        guild = discord.Object(id=GUILD_ID)
        await tree.sync(guild=guild)
        await tree.sync()
        print(f'✅ Bot conectado como {client.user}')
        print(f'✅ Comandos sincronizados en el servidor')
        
        # Enviar mensaje permanente con botón en el canal #ofertas
        ofertas_channel = client.get_channel(OFERTAS_CHANNEL_ID)
        if ofertas_channel:
            # Limpiar mensajes anteriores del bot (opcional)
            async for message in ofertas_channel.history(limit=10):
                if message.author == client.user:
                    await message.delete()
            
            # Mensaje con normas y botón
            normas_message = """👋 **¡A negociar y disfrutar!** ⚽👊

👉 **CREA UNA OFERTA:**

Haz clic derecho en este mensaje ➜ **Crear hilo** ➜ Nombra tu oferta ➜ Añade al manager con @ ➜ ¡Negociad!

Cada oferta tendrá su propio hilo privado que se cerrará automáticamente cuando termine la negociación.

**📋 Recuerda las normas:**
⛔ **No se puede pagar la cláusula durante una negociación activa**
✅ **Tras finalizar, se puede hacer clausulazo**
⏰ **Clausulazos solo h** asta: **jueves a las 12:00**
🔒 **Jugador cuya cláusula se negocia:** No puede modificar su cláusula hasta que termine la jornada

🔽 **Haz clic en el botón para crear una oferta:**
            """
            
            view = PersistentOfferView()
            await ofertas_channel.send(normas_message, view=view)
            print(f'✅ Mensaje con botón enviado en #{ofertas_channel.name}')
    except Exception as e:
        print(f'❌ Error al sincronizar comandos: {e}')

client.run(TOKEN)
