import discord
from discord.ext import commands
import json
import os
import datetime
from flask import Flask
from threading import Thread
from dotenv import load_dotenv

.# Cargar token
load_dotenv()

.# Intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
# Inicialización del Bot
bot = commands.Bot(command_prefix='!', intents=intents)

# --- CONEXIÓN Y CREACIÓN DE LA BASE DE DATOS (SQLite) ---
DB_FILE = 'mi_bot_data.db'
db = sqlite3.connect(DB_FILE)
cursor = db.cursor()

# Creación de la tabla 'users'
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        balance INTEGER DEFAULT 0,
        last_daily TEXT DEFAULT '0' 
    )
""")
db.commit()
# --------------------------------------------------------

# Evento: Bot Listo
@bot.event
async def on_ready():
    print(f'🤖 Bot conectado como: {bot.user.name}')
    print('✅ Sistema de Niveles/Economía operativo.')
    print('-------------------------------------')

# Evento: Lógica de Nivelación (on_message)
XP_BASE = 100
XP_EXPONENT = 2 

@bot.event
async def on_message(message):
    if message.author.bot or not message.content:
        return

    user_id = message.author.id
    
    try:
        # Obtener o crear usuario
        cursor.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,))
        data = cursor.fetchone()

        if data is None:
            cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            db.commit()
            xp_actual, nivel_actual = 0, 0
        else:
            xp_actual, nivel_actual = data

        # Sumar XP
        xp_ganada = random.randint(15, 25)
        nueva_xp = xp_actual + xp_ganada
        xp_requerida = XP_BASE * (nivel_actual + 1)**XP_EXPONENT

        if nueva_xp >= xp_requerida:
            # Subida de Nivel
            nuevo_nivel = nivel_actual + 1
            xp_restante = nueva_xp - xp_requerida
            
            cursor.execute("UPDATE users SET xp = ?, level = ? WHERE user_id = ?",
                           (xp_restante, nuevo_nivel, user_id))
            db.commit()
            
            await message.channel.send(f"**¡Félicitations, {message.author.mention}!** ¡Has alcanzado el **Nivel {nuevo_nivel}**!")
        
        else:
            # Solo actualizar la XP
            cursor.execute("UPDATE users SET xp = ? WHERE user_id = ?",
                           (nueva_xp, user_id))
            db.commit()

    except Exception as e:
        print(f"Error en on_message/DB: {e}")
        db.rollback() 

    # Permite que los comandos (!daily, !balance) funcionen
    await bot.process_commands(message)

    # Comando: Ver saldo
@bot.command(name='balance', aliases=['bal'])
async def balance(ctx):
    user_id = ctx.author.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    
    if data:
        saldo = data[0]
        await ctx.send(f"Tu saldo actual es de **{saldo} monedas**.")
    else:
        await ctx.send("¡Envía un mensaje para ser registrado en el sistema!")

# Comando: Recompensa diaria
@bot.command(name='daily')
async def daily(ctx):
    user_id = ctx.author.id
    daily_reward = 500 
    
    cursor.execute("SELECT balance, last_daily FROM users WHERE user_id = ?", (user_id,))
    data = cursor.fetchone()
    
    if data is None: 
        await ctx.send("¡Envía un mensaje para ser registrado en el sistema primero!")
        return

    saldo_actual, last_daily_str = data
    
    # Lógica de Cooldown (24 horas)
    if last_daily_str != '0':
        last_daily = datetime.datetime.strptime(last_daily_str, '%Y-%m-%d %H:%M:%S.%f')
        time_diff = datetime.datetime.now() - last_daily
        
        if time_diff.total_seconds() < 86400: # 86400 segundos = 24 horas
            tiempo_restante = 86400 - time_diff.total_seconds()
            horas = int(tiempo_restante // 3600)
            minutos = int((tiempo_restante % 3600) // 60)
            await ctx.send(f"Debes esperar **{horas}h {minutos}m** para tu próxima recompensa diaria.")
            return

    # Si puede reclamar
    nuevo_saldo = saldo_actual + daily_reward
    fecha_actual = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    
    cursor.execute("UPDATE users SET balance = ?, last_daily = ? WHERE user_id = ?",
                   (nuevo_saldo, fecha_actual, user_id))
    db.commit()
    
    await ctx.send(f"¡Has reclamado tu recompensa diaria de **{daily_reward} monedas**! Nuevo saldo: **{nuevo_saldo}**.")

    # --- INICIO DEL BOT ---
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Ocurrió un error al intentar iniciar el bot: {e}")
     
# Evento al iniciar
@bot.event
async def on_ready():
    print(f":crystal_ball: Bot conectado como {bot.user}")

# Servidor web para evitar que Render lo duerma
app = Flask('')

@app.route('/')
def home():
    return "Bot activo"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# Ejecutar bot
bot.run(os.getenv("TOKEN")) 

