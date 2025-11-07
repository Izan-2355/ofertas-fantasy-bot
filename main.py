import discord
from discord import app_commands
from discord.ui import Select, View, Button
import os
import asyncio

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
        
    # Auto-eliminar el modal después de 3 minutos
    await asyncio.sleep(180) # 180 segundos = 3 minutos
    try:
        await interaction.delete_original_response()
    except:
        pass # Por si el mensaje ya fue eliminado

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
            # Obtener posición para insertar entre Fantasy y Modo Carreras
    fantasy_category = discord.utils.get(guild.categories, name="Fantasy")
    modo_carreras_category = discord.utils.get(guild.categories, name="Modo Carreras")
    
    # Calcular la posición: entre Fantasy y Modo Carreras
    if fantasy_category and modo_carreras_category:
        fantasy_pos = fantasy_category.position
        modo_carreras_pos = modo_carreras_category.position
        position = max(fantasy_pos, modo_carreras_pos - 1) + 1
    else:
        position = None  # Dejar en la posición por defecto
    
    # Crear categoría con posición especificada
    category = await guild.create_category(category_name, overwrites=overwrites, position=position)
        
        # Crear canal de voz
        voice_channel = await guild.create_voice_channel("🔊 Voz", category=category)
        
        # Crear canal de texto
        text_channel = await guild.create_text_channel("💬 Negociación", category=category)
        
        # Vista con botones para el canal de texto
        view = View(timeout=None)
        close_votes = set()  # Para rastrear quién votó para cerrar
        
        # Botón Contraoferta
        contraoferta_button = Button(label="🔄 Contraoferta", style=discord.ButtonStyle.secondary, custom_id=f"contraoferta_{offer_counter}")
        async def contraoferta_callback(button_interaction: discord.Interaction):
            if button_interaction.user != creator and button_interaction.user != target_member:
                await button_interaction.response.send_message("❌ Solo los participantes pueden usar este botón", ephemeral=True)
                return
            
            await button_interaction.response.send_message(f"✅ {button_interaction.user.mention} ha hecho una contraoferta", ephemeral=False)
        
        contraoferta_button.callback = contraoferta_callback
        view.add_item(contraoferta_button)
        
        # Botón Cerrar con votación
        cerrar_button = Button(label="🔒 Cerrar Oferta", style=discord.ButtonStyle.danger, custom_id=f"cerrar_{offer_counter}")
        async def cerrar_callback(button_interaction: discord.Interaction):
            nonlocal close_votes
            if button_interaction.user != creator and button_interaction.user != target_member:
                await button_interaction.response.send_message("❌ Solo los participantes pueden cerrar la oferta", ephemeral=True)
                return
            
            # Añadir voto
            close_votes.add(button_interaction.user.id)
            
            # Verificar si ambos participantes votaron
            if creator.id in close_votes and target_member.id in close_votes:
                await button_interaction.response.send_message(
                    f"✅ Ambos participantes confirmaron el cierre.\n⏰ La oferta se eliminará automáticamente en **1 hora**.\n\n💡 Tienes tiempo para revisar lo acordado.",
                    ephemeral=False
                )
                
                # Esperar 1 hora antes de eliminar
                await asyncio.sleep(3600)  # 3600 segundos = 1 hora
                
                # Eliminar categoría y canales
                for channel in category.channels:
                    await channel.delete()
                await category.delete()
                
                # Eliminar de ofertas activas
                if offer_counter in active_offers:
                    del active_offers[offer_counter]
            else:
                # Solo un participante votó
                voted_user = button_interaction.user.mention
                pending_user = target_member.mention if button_interaction.user == creator else creator.mention
                await button_interaction.response.send_message(
                    f"✋ {voted_user} quiere cerrar la oferta.\n⏳ Esperando confirmación de {pending_user}...",
                    ephemeral=False
                )
        
        cerrar_button.callback = cerrar_callback
        view.add_item(cerrar_button)
        
        # Mensaje inicial en el canal de texto (mejorado y estiloso)
        welcome_msg = f"""╔══════════════════════════════════════╗
║   🤝 **NEGOCIACIÓN INICIADA** 🤝      ║
╚══════════════════════════════════════╝

**📊 Oferta #{offer_counter}**

┌─────────────────────────────────┐
│ **👥 PARTICIPANTES**
├─────────────────────────────────┤
│ • {creator.mention}
│ • {target_member.mention}
└─────────────────────────────────┘

╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
┃  📋 **NORMAS DE NEGOCIACIÓN**
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯

⛔ **NO** se puede pagar la cláusula durante negociación activa
✅ **Tras finalizar**, se puede hacer el clausulazo
⏰ **Clausulazos** permitidos hasta: **Jueves 12:00**
🔒 **Jugador negociado**: NO puede modificar su cláusula hasta fin de jornada

╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
┃  🎮 **CONTROLES**
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯

🔄 **Contraoferta** → Permite al otro participante responder
🔒 **Cerrar Oferta** → Ambos participantes deben confirmar

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**¡Buena suerte en la negociación!** 🍀⚽
        """
        
        await text_channel.send(welcome_msg, view=view)
        
        # Guardar oferta activa
        active_offers[offer_counter] = {
            'category': category.id,
            'creator': creator.id,
            'target': target_member.id
        }
        
        # Mensaje de confirmación efímero con auto-eliminación en 3 minutos
        confirmation_msg = await interaction.response.send_message(
            f"✅ **Oferta creada exitosamente**\n\n📂 Categoría: {category.name}\n🔊 Canal de voz: {voice_channel.mention}\n💬 Canal de texto: {text_channel.mention}\n\n⏰ Este mensaje se eliminará automáticamente en 3 minutos.",
            ephemeral=True
        )
        
        # Incrementar contador
        offer_counter += 1
        
        # Eliminar mensaje de confirmación después de 3 minutos
        await asyncio.sleep(180)  # 180 segundos = 3 minutos
        try:
            await interaction.delete_original_response()
        except:
            pass  # Por si el mensaje ya fue eliminado
        
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
            
            # Mensaje con normas y botón (mejorado y estiloso)
            normas_message = """╔═══════════════════════════════════════╗
║  👋 **¡A NEGOCIAR Y DISFRUTAR!** ⚽👊  ║
╚═══════════════════════════════════════╝

╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
┃  📋 **RECUERDA LAS NORMAS**
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯

⛔ **No se puede pagar la cláusula** durante una negociación activa
✅ **Tras finalizar**, se puede hacer clausulazo
⏰ **Clausulazos solo hasta**: **Jueves a las 12:00**
🔒 **Jugador cuya cláusula se negocia**: No puede modificarla hasta que termine la jornada

╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
┃  🎯 **¿LISTO PARA NEGOCIAR?**
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯

🔽 **Haz clic en el botón de abajo para crear una oferta**
            """
            
            view = PersistentOfferView()
            await ofertas_channel.send(normas_message, view=view)
            print(f'✅ Mensaje con botón enviado en #{ofertas_channel.name}')
    except Exception as e:
        print(f'❌ Error al sincronizar comandos: {e}')

client.run(TOKEN)
