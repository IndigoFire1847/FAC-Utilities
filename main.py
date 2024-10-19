import discord
import os
import sys
import json
import random
import requests
import asyncio
import time

from collections import defaultdict
from datetime import datetime
from discord import app_commands
from discord.utils import get
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True

OWNER_ID = 683313053605167185 # replace with your ID

client = commands.Bot(command_prefix='-', intents=intents)
WEATHERKEY = # your weather key here (for the weather command, can be taken out)
BASE_URL = #  (Insert your url for your weather API, again optional)
TOKEN = # Place your bots key here


@client.event
async def on_ready():
  print("ready")
  try:
    synced = await client.tree.sync()
    print(f"synced {len(synced)} command(s)")
  except Exception as e:
    print(e)



@client.event
async def on_member_join(member):
    # Define the role ID (more reliable than role name)
    role_id = 1234567891011121314  # Replace with the actual role ID

    # Get the role object using the role ID
    role = member.guild.get_role(role_id)

    if role is not None:
        # Add the role to the member
        await member.add_roles(role)
        print(f"Assigned {role.name} to {member.display_name}")
    else:
        print(f"Role with ID {role_id} not found.")

# Load or create leveling data
if not os.path.exists("levels.json"):
    with open("levels.json", "w") as f:
        json.dump({}, f)

# Load the leveling data
def load_data():
    with open("levels.json", "r") as f:
        return json.load(f)

# Save the leveling data
def save_data(data):
    with open("levels.json", "w") as f:
        json.dump(data, f, indent=4)

# Helper function to add XP
def add_xp(user_id, xp_to_add):
    data = load_data()
    if str(user_id) not in data:
        data[str(user_id)] = {"xp": 0, "level": 1}

    data[str(user_id)]["xp"] += xp_to_add

    # Level up if XP threshold is reached
    current_xp = data[str(user_id)]["xp"]
    current_level = data[str(user_id)]["level"]
    xp_needed = 5 * (current_level ** 2) + 50 * current_level + 100

    if current_xp >= xp_needed:
        data[str(user_id)]["level"] += 1
        data[str(user_id)]["xp"] = current_xp - xp_needed
        return True, data[str(user_id)]["level"]
    else:
        save_data(data)
        return False, None

# Assign roles when users reach specific levels
async def assign_roles(member, new_level):
    roles_to_assign = {
        5: "Level 5", # change to your level roles (can add more if needed)
        10: "Level 10",
        15: "Level 15"
    }

    guild_roles = {role.name: role for role in member.guild.roles}

    for level, role_name in roles_to_assign.items():
        if new_level >= level and role_name in guild_roles:
            role = guild_roles[role_name]
            if role not in member.roles:
                await member.add_roles(role)
                await member.send(f"Congrats! You've been given the **{role_name}** role for reaching level {level}!")

### Event Listener for Message Events ###
@client.event
async def on_message(message):
    if message.author.bot:
        return

    # Add random XP for each message sent
    xp_to_add = random.randint(5, 15)
    leveled_up, new_level = add_xp(message.author.id, xp_to_add)

    # If the user leveled up, send a message and assign roles
    if leveled_up:
        await message.channel.send(f"🎉 {message.author.mention} has reached level {new_level}!")
        await assign_roles(message.author, new_level)

    await client.process_commands(message)  # Process other bot commands

### Command to Check User Level ###
@client.tree.command(name="level", description="Check your current level and XP")
async def level(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_data()

    if user_id not in data:
        await interaction.response.send_message("You don't have any XP yet!")
    else:
        xp = data[user_id]["xp"]
        level = data[user_id]["level"]
        await interaction.response.send_message(f"{interaction.user.mention}, you are at **level {level}** with **{xp} XP**!")

### Command to Check Another User's Level ###
@client.tree.command(name="level_of", description="Check another user's level and XP")
async def level_of(interaction: discord.Interaction, member: discord.Member):
    user_id = str(member.id)
    data = load_data()

    if user_id not in data:
        await interaction.response.send_message(f"{member.display_name} doesn't have any XP yet!")
    else:
        xp = data[user_id]["xp"]
        level = data[user_id]["level"]
        await interaction.response.send_message(f"{member.display_name} is at **level {level}** with **{xp} XP**!")

### Command to Show Leaderboard ###
@client.tree.command(name="leaderboard", description="Show the top 10 users with the highest levels")
async def leaderboard(interaction: discord.Interaction):
    data = load_data()
    sorted_users = sorted(data.items(), key=lambda x: (x[1]['level'], x[1]['xp']), reverse=True)[:10]

    leaderboard_msg = "**Top 10 Users by Level:**\n"
    for idx, (user_id, stats) in enumerate(sorted_users, 1):
        user = await client.fetch_user(user_id)
        leaderboard_msg += f"{idx}. {user.display_name} - Level {stats['level']} ({stats['xp']} XP)\n"

    await interaction.response.send_message(leaderboard_msg)

### Error Handler for Commands ###
@client.tree.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)


def get_weather(city):
  params = {
      'q': city,
      'appid': WEATHERKEY,
      'units': 'metric'  # You can use 'imperial' for Fahrenheit
  }
  response = requests.get(BASE_URL, params=params)
  return response.json()


# Function to get the weather data
def get_weather_data(city: str, units: str = 'metric'):
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        'q': city,
        'appid': WEATHERKEY,
        'units': units
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        return None

# Function to convert Unix time to a readable format
def unix_to_readable_time(unix_time: int):
    return datetime.utcfromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S UTC')

# Weather Command
@client.tree.command(name="weather", description="Get the current weather for a city.")
@app_commands.describe(city="Enter the city", units="Temperature unit (Celsius or Fahrenheit)")
async def weather_command(interaction: discord.Interaction, city: str, units: str = 'Celsius'):
    units = 'imperial' if units.lower() == 'fahrenheit' else 'metric'
    data = get_weather_data(city, units)

    if data:
        # Extracting necessary data
        city_name = data['name']
        country_code = data['sys']['country']
        weather_desc = data['weather'][0]['description'].title()
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        pressure = data['main']['pressure']
        wind_speed = data['wind']['speed']
        visibility = data.get('visibility', 'N/A') / 1000  # Convert meters to kilometers
        icon = data['weather'][0]['icon']
        sunrise = unix_to_readable_time(data['sys']['sunrise'])
        sunset = unix_to_readable_time(data['sys']['sunset'])

        # Create an embed with the weather information
        embed = discord.Embed(
            title=f"Weather in {city_name}, {country_code}",
            color=discord.Color.blue(),
            description=f"**{weather_desc}**"
        )
        embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon}.png")

        # Adding weather fields
        embed.add_field(name="Temperature", value=f"{temp}°{'C' if units == 'metric' else 'F'}", inline=True)
        embed.add_field(name="Feels Like", value=f"{feels_like}°{'C' if units == 'metric' else 'F'}", inline=True)
        embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
        embed.add_field(name="Pressure", value=f"{pressure} hPa", inline=True)
        embed.add_field(name="Visibility", value=f"{visibility} km", inline=True)
        embed.add_field(name="Wind Speed", value=f"{wind_speed} m/s", inline=True)
        embed.add_field(name="Sunrise", value=sunrise, inline=True)
        embed.add_field(name="Sunset", value=sunset, inline=True)

        embed.set_footer(text="Weather data provided by OpenWeatherMap")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    else:
        await interaction.response.send_message(f"Could not retrieve weather data for **{city}**. Please check the city name and try again.", ephemeral=True)


# Autocomplete for city names (Optional: Requires a list of cities)
@weather_command.autocomplete('city')
async def city_autocomplete(interaction: discord.Interaction, current: str):
    cities = ["New York", "Los Angeles", "London", "Tokyo", "Paris", "Berlin", "Sydney", "Edinburgh"]
    # Return city suggestions that match the current input
    return [app_commands.Choice(name=city, value=city) for city in cities if current.lower() in city.lower()]



# Ping Command

@client.tree.command(description="gets the bots ping!")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(title="ARL Bot ping")
    embed.add_field(name="Bot ping", value=f"{round(client.latency * 1000)}ms")
    await interaction.response.send_message(embed=embed, ephemeral = True)

@client.tree.command(name='eval', description='Evaluates Python code or executes a command')
async def eval_command(interaction: discord.Interaction, code: str):
    # Check if the author is the owner
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)

    # Prepare the code for execution
    code = code.strip('`')  # Strip backticks if present

    try:
        # Define an async wrapper with local context
        exec(
            f'async def _eval_wrapper(interaction): ' + ''.join(f'\n {line}' for line in code.split('\n'))
        )

        # Execute the async wrapper and pass the interaction into it
        await locals()['_eval_wrapper'](interaction)

        await interaction.response.send_message(f"Executed: `{code}`", ephemeral=True)
    except Exception as e:
        # Send the error message in case of failure
        await interaction.response.send_message(f'Error: {str(e)}', ephemeral=True)

# Give role command

@client.tree.command(description = "give a user a role")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(member = "Which user am i giving a role to", role = "Which role am i giving to the user")
async def addrole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await interaction.response.send_message(f"{role} was given to {member.mention}")
    await member.send(f"you were given {role} by {interaction.user}")

# Remove role command

@client.tree.command(description = "remove a role from a user")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(member = "Which user am i removing a role from", role = "Which role am i removing from the the user")
async def removerole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if role and role in member.roles:
        await member.remove_roles(role)
        await interaction.response.send_message(f"Removed the role **{role}** from {member.mention}.", ephemeral=True)
        await member.send(f"{role} was removed from you by {interaction.user}")
    else:
        await interaction.response.send_message(f"Either the role **{role}** doesn't exist, or {member} doesn't have it.", ephemeral=True)

# FsHub command (Change URL to your own airline)
@client.tree.command(description="Recieve the link to our FsHub airline")
async def fshub(interaction: discord.Interaction):
     await interaction.response.send_message("The link to our FsHub airline is https://fshub.io/airline/FCA/overview", ephemeral=True)   


# Role delete command

@client.tree.command(description="Remove a role")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(role = "what role am i deleting?", reason = "Why am i deleting this role")
async def delrole(interaction: discord.Interaction, role: discord.Role, reason: str):
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)

    if not role:
        await interaction.response.send_message(f"Role '{role}' not found.", ephemeral=True)
        return

    await role.delete()
    await interaction.response.send_message(f"Role '{role}' removed successfully because {reason}", ephemeral=True)

# Kick command

@client.tree.command(description="kick a user")
@app_commands.checks.has_permissions(kick_members=True)
@app_commands.describe(user = "Who am i kicking?", reason = "Why am i kicking them?")
async def kick(interaction: discord.Interaction, user: discord.User, reason:str):
  if interaction.guild is None:
    await interaction.response.send_message("This command can only be used in a server."
                                            , ephemeral=True)
    return

  try:
    await interaction.guild.kick(user, reason=reason)
    await interaction.response.send_message(f'successfully kicked {user.mention}'
   f'with reason {reason}', ephemeral=True)
    await user.send(f'you have been kicked with reason {reason}')
  except discord.Forbidden:
    await interaction.response.send_message('I do not have permission' 
    'to kick this user', ephemeral=True)

@client.tree.command(name="roles", description="List all roles in the server.")
async def roles(interaction: discord.Interaction):
    roles = [role.mention for role in interaction.guild.roles if role.name != "@everyone"]
    await interaction.response.send_message(f"Roles in {interaction.guild.name}: {', '.join(roles)}")

# Utility: Get bot uptime
start_time = datetime.utcnow()

@client.tree.command(name="uptime", description="Check how long the bot has been running.")
async def uptime(interaction: discord.Interaction):
    now = datetime.utcnow()
    uptime_duration = now - start_time
    days, remainder = divmod(int(uptime_duration.total_seconds()), 86400)
    hours, remainder = divmod(int(uptime_duration.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await interaction.response.send_message(f"I have been online for {days}d {hours}h {minutes}m {seconds}s")

@client.tree.command(name="userinfo", description="Get information about a user.")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user

    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    joined_at = member.joined_at.strftime("%Y-%m-%d %H:%M:%S")
    created_at = member.created_at.strftime("%Y-%m-%d %H:%M:%S")

    embed = discord.Embed(title=f"User Info: {member}", color=discord.Color.green())
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
    embed.add_field(name="Joined", value=joined_at, inline=True)
    embed.add_field(name="Account Created", value=created_at, inline=False)
    embed.add_field(name="Roles", value=", ".join(roles), inline=False)
    embed.set_thumbnail(url=member.avatar.url)

    await interaction.response.send_message(embed=embed)

@client.tree.command(name="serverinfo", description="Get information about the server.")
async def server_info(interaction: discord.Interaction):
    server = interaction.guild
    num_channels = len(server.channels)
    num_members = server.member_count
    creation_date = server.created_at.strftime("%Y-%m-%d %H:%M:%S")

    embed = discord.Embed(title=f"Server Info: {server.name}", color=discord.Color.blue())
    embed.add_field(name="Server ID", value=server.id, inline=True)
    embed.add_field(name="Members", value=num_members, inline=True)
    embed.add_field(name="Channels", value=num_channels, inline=True)
    embed.add_field(name="Creation Date", value=creation_date, inline=False)
    embed.set_thumbnail(url=server.icon.url)

    await interaction.response.send_message(embed=embed)

# Ban command

@client.tree.command(description="ban a user")
@app_commands.checks.has_permissions(ban_members=True)
@app_commands.describe(user = "Who am i banning?", reason = "Why am i banning them?")
async def ban(interaction: discord.Interaction, user: discord.User, reason:str):
  if interaction.guild is None:
    await interaction.response.send_message("This command can only be used in a server."
                                            , ephemeral=True)
    return

  try:
    await interaction.guild.ban(user, reason=reason)
    await interaction.response.send_message(f'successfully banned {user.mention}'
   f' with reason {reason}', ephemeral=True)
    await user.send(f'you have been banned for {reason}')
  except discord.Forbidden:
    await interaction.response.send_message('I do not have permission' 
    'to ban this user', ephemeral=True)

# Unban command

@client.tree.command(description="unban a user")
@app_commands.describe(user = "who am i unbanning?", reason = "why am i unbanning them?")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user: discord.User, reason:str):
      if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server."
                                                , ephemeral=True)
        return
      try:
        await interaction.guild.unban(user, reason=reason)
        await interaction.response.send_message(f"unbanned {user.mention} with reason {reason}", ephemeral=True)
      except discord.Forbidden:
        await interaction.response.send_message('I do not have permission' 
'to ban this user', ephemeral=True)

# Warm command (not a moderation command)

@client.tree.command(description="warm a user")
@app_commands.describe(user ="Who am i warming")
@app_commands.checks.has_permissions(manage_messages=True)
async def warm(interaction: discord.Interaction, user: discord.User):
  await interaction.response.send_message(f"warmed {user.mention}")
  await user.send(f"You were warmed in FAC by {interaction.user}")


# Purge command

@client.tree.command(description="delete a specified amount of messages in a channel")
@app_commands.checks.has_permissions(manage_messages=True)
@app_commands.describe(amount = "How many messages should i delete?")
async def purge(interaction: discord.Interaction, amount: int):
  if interaction.guild is None:
    await interaction.response.send_message("This command only works in a server."
                                            , ephemeral=True)
    return
  if isinstance(interaction.channel, discord.TextChannel):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"Cleared {amount} messages!", ephemeral=True)                               
  else:
    await interaction.response.send_message("This command only works in a text channel."
                                            , ephemeral=True)

# bot shutdown command

@client.tree.command(name="shutdown", description="Shuts down the bot.")
async def shutdown(interaction: discord.Interaction):
    if interaction.user.id == OWNER_ID:
        await interaction.response.send_message("Shutting down...")
        await client.close()
    else:
        await interaction.response.send_message("You do not have permission to use this"
                                                "command.", ephemeral=True)

# Restart command
@client.tree.command(description="Restarts the bot.")
async def restart(interaction: discord.Interaction):
    if interaction.user.id == OWNER_ID:
        await interaction.response.send_message("Restarting the bot...")
        os.execv(sys.executable, ['python'] + sys.argv)
    else:
        await interaction.response.send_message("You do not have permission to use this" 
                                                "command.", ephemeral=True)

# Set the bot's status
@client.tree.command(name="setstatus", description="Sets the bot's status.")
@discord.app_commands.describe(status="The status message to set for the bot")
async def set_status(interaction: discord.Interaction, status: str):
    if interaction.user.id == OWNER_ID:
        await client.change_presence(activity=discord.Game(name=status))
        await interaction.response.send_message(f"Status updated to: {status}"
                                                , ephemeral=True)
    else:
        await interaction.response.send_message("You do not have permission to use this"
                                                "command.", ephemeral=True)

# Slowmode Command 

@client.tree.command(name="slowmode", description="Set a slowmode delay in a channel")
@app_commands.checks.has_permissions(administrator=True)
async def slowmode(interaction: discord.Interaction, seconds: int):
    channel = interaction.channel

    # Check if the delay is within acceptable range
    if 0 <= seconds <= 21600:  # Discord allows slowmode between 0 and 6 hours (21600 seconds)
        await channel.edit(slowmode_delay=seconds)
        await interaction.response.send_message(f"Slowmode has been set to {seconds} seconds in {channel.mention}.", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid time! Slowmode must be between 0 and 21600 seconds (6 hours).", ephemeral=True)



# Poll command

@client.tree.command(description="create a poll")
@app_commands.describe(question = "What am i making a poll about?", option1 = "What is your first option?", option2 = "what is your second option?", option3 = "What is your third option")
@app_commands.checks.has_permissions(manage_messages=True)
async def poll(interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None):
      if option3 != None:
        await interaction.response.send_message("Poll Created", ephemeral = True)
        message = f"{question}: \n1️⃣ = {option1}\n2️⃣ = {option2}\n3️⃣ = {option3}"
        message = await interaction.channel.send(message) # Store the message object
        await message.add_reaction('1️⃣')
        await message.add_reaction('2️⃣')
        await message.add_reaction('3️⃣')
      else:
        await interaction.response.send_message("poll created!", ephemeral = True)
        message = f"{question}: \n1️⃣ = {option1}**\n**2️⃣ = {option2}"
        message = await interaction.channel.send(message) # Store the message object
        await message.add_reaction('1️⃣')
        await message.add_reaction('2️⃣')

# Provides link to this page

@client.tree.command(description="Get the source code for the bot")
async def code(interaction: discord.Interaction):
  await interaction.response.send_message("The link to my source code is here (temporarily outdated): https://github.com/IndigoFire1847/FAC-Utilities/tree/main", ephemeral=True)

# Handler for poll command if user doesn't have permissions




# Helper function to create paginated embeds
def create_help_embeds():
    commands_list = {
        "/serverinfo": "Get information about the server.",
        "/userinfo [member]": "Get information about a specific user or yourself.",
        "/ping": "Check the bot's latency.",
        "/kick [member] [reason]": "Kick a member from the server.",
        "/ban [member] [reason]": "Ban a member from the server.",
        "/clear [amount]": "Clear a number of messages from the channel.",
        "/uptime": "Check how long the bot has been online.",
        "/roles": "List all roles in the server.",
        "/poll [question] [option1] [option2]": "Create a poll with two options."
    }

    # Split commands into pages, each page having up to 4 commands for easier reading
    items_per_page = 4
    pages = [list(commands_list.items())[i:i + items_per_page] for i in range(0, len(commands_list), items_per_page)]

    embeds = []
    for i, page in enumerate(pages):
        embed = discord.Embed(title=f"Help - Command List (Page {i + 1}/{len(pages)})", color=discord.Color.blue())
        for command, description in page:
            embed.add_field(name=command, value=description, inline=False)
        embed.set_footer(text="Use each command with the specified format.")
        embeds.append(embed)

    return embeds


# Define the Paginator View for buttons
class HelpPaginator(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=180)  # Set timeout for the paginator view (optional)
        self.embeds = embeds
        self.current_page = 0

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, disabled=True)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        await self.update_buttons(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        await self.update_buttons(interaction)

    async def update_buttons(self, interaction):
        # Disable buttons based on the current page
        if self.current_page == 0:
            self.previous_button.disabled = True
        else:
            self.previous_button.disabled = False

        if self.current_page == len(self.embeds) - 1:
            self.next_button.disabled = True
        else:
            self.next_button.disabled = False

        # Update the embed and the buttons
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


# Custom Help Command with Pagination
@client.tree.command(name="help", description="Display a list of all commands with pagination.")
async def help_command(interaction: discord.Interaction):
    embeds = create_help_embeds()

    # If only one page exists, just send the single embed without buttons
    if len(embeds) == 1:
        await interaction.response.send_message(embed=embeds[0])
    else:
        paginator = HelpPaginator(embeds)
        await interaction.response.send_message(embed=embeds[0], view=paginator)

# Path to the JSON file
AFK_FILE_PATH = 'afk_statuses.json'

# Load AFK statuses from JSON file
def load_afk_statuses():
    try:
        with open(AFK_FILE_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # Return an empty dict if the file doesn't exist or is empty

# Save AFK statuses to JSON file
def save_afk_statuses(afk_statuses):
    with open(AFK_FILE_PATH, 'w') as f:
        json.dump(afk_statuses, f)

# Load AFK statuses at startup
afk_statuses = load_afk_statuses()

# Command to set AFK status
@client.tree.command(name="afk", description="Set your AFK status.")
@app_commands.describe(reason="Optional reason for being AFK.")
async def afk(interaction: discord.Interaction, reason: str = "No reason provided."):
    user_id = str(interaction.user.id)  # Use string for JSON keys
    afk_statuses[user_id] = reason  # Store AFK status with reason
    save_afk_statuses(afk_statuses)  # Save to JSON
    await interaction.response.send_message(f"You are now AFK: {reason}", ephemeral=True)

# Event to handle message mentions
@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Reload AFK statuses from JSON to ensure latest data
    afk_statuses = load_afk_statuses()

    # Check if any mentioned user is AFK
    for user in message.mentions:
        if str(user.id) in afk_statuses:
            reason = afk_statuses[str(user.id)]
            await message.reply(f"{user} is AFK: {reason}", mention_author = True)
            await asyncio.sleep(5)
            await message.delete()

    # Process commands after handling mentions
            await client.process_commands(message)

# Command to remove AFK status
@client.tree.command(name="back", description="Remove your AFK status.")
async def deAFK(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in afk_statuses:
        del afk_statuses[user_id]  # Remove AFK status
        save_afk_statuses(afk_statuses)  # Save to JSON
        await interaction.response.send_message("You are now back!", ephemeral=True)
    else:
        await interaction.response.send_message("You are not AFK.", ephemeral=True)

# File path to store the warnings
WARNINGS_FILE = "warnings.json"

# Load warnings from JSON file or create a new one
def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save warnings to the JSON file
def save_warnings(warnings):
    with open(WARNINGS_FILE, "w") as f:
        json.dump(warnings, f, indent=4)

# Initialize warnings dictionary from the file
warnings = load_warnings()

# List of prohibited words (you can customize this list)
PROHIBITED_WORDS = ["cunt", "nigger", "nigga", "Koon"]

# Dictionary to track user message timestamps for spam detection
user_message_times = defaultdict(list)

# Automod system to check messages for prohibited content and spam
@client.event
async def on_message(message):
    if message.author == client.user:
        return  # Ignore messages sent by the bot itself

    user_id = str(message.author.id)

    # Check for prohibited words
    if any(word in message.content.lower() for word in PROHIBITED_WORDS):
        await message.delete()       
        await handle_warning(message.author, "Used prohibited word(s)", message.channel)


    # Check for spam
    current_time = time.time()
    user_message_times[user_id].append(current_time)

    # Keep only timestamps from the last 10 seconds (adjust as needed)
    user_message_times[user_id] = [t for t in user_message_times[user_id] if current_time - t < 10]

    # If the user sent more than 5 messages in the last 10 seconds, warn them
    if len(user_message_times[user_id]) > 5:
        await handle_warning(message.author, "Spamming messages", message.channel)

async def handle_warning(user, reason, channel):
    user_id = str(user.id)

    if user_id not in warnings:
        warnings[user_id] = []

    warnings[user_id].append(reason)

    # Save the updated warnings to the file
    save_warnings(warnings)

    # Check if the user has reached 4 warnings
    if len(warnings[user_id]) >= 4:
        try:
            # Kick the user and reset their warnings
            await user.kick(reason="Reached 4 warnings")
            warnings[user_id] = []
            save_warnings(warnings)  # Save the reset warnings
            await channel.send(f'{user.mention} has been kicked for reaching 4 warnings due to spamming or prohibited words.')
        except discord.Forbidden:
            await channel.send("I do not have permission to kick this user.")
    else:
        await channel.send(f'{user.mention}, you have been warned for {reason}. You now have {len(warnings[user_id])} warning(s).')
        await user.send(f'You have been warned in {channel.guild.name} for {reason}. You have {len(warnings[user_id])} warning(s).')

# Command to issue a warning to a user
@client.tree.command(name="warn", description="Warn a user for a specific reason")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    if member.bot:
        await interaction.response.send_message("You cannot warn a bot.", ephemeral=True)
        return

    user_id = str(member.id)  # Store user ID as string for JSON compatibility

    if user_id not in warnings:
        warnings[user_id] = []

    warnings[user_id].append(reason)

    # Save the updated warnings to the file
    save_warnings(warnings)

    # Check if the user has reached 4 warnings
    if len(warnings[user_id]) >= 4:
        try:
            # Kick the user and reset their warnings
            await member.kick(reason="Reached 4 warnings")
            warnings[user_id] = []
            save_warnings(warnings)  # Save the reset warnings
            await interaction.response.send_message(f'{member.mention} has been kicked for reaching 4 warnings.')
        except discord.Forbidden:
            await interaction.response.send_message("I do not have permission to kick this user.", ephemeral=True)
    else:
        await interaction.response.send_message(f'{member.mention} has been warned. Reason: {reason}')
        await member.send(f'You have been warned in {interaction.guild.name} for: {reason}. You have {len(warnings[user_id])} warning(s).')


# Command to view warnings of a user
@client.tree.command(name="warnings", description="View warnings for a user")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def view_warnings(interaction: discord.Interaction, member: discord.Member):
    user_id = str(member.id)
    if user_id in warnings and warnings[user_id]:
        warn_list = '\n'.join([f"{i + 1}. {w}" for i, w in enumerate(warnings[user_id])])
        await interaction.response.send_message(f'{member.mention} has the following warnings:\n{warn_list}')
    else:
        await interaction.response.send_message(f'{member.mention} has no warnings.')


# Command to clear warnings of a user
@client.tree.command(name="clearwarnings", description="Clear all warnings for a user")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def clear_warnings(interaction: discord.Interaction, member: discord.Member):
    user_id = str(member.id)
    if user_id in warnings:
        warnings[user_id] = []
        save_warnings(warnings)  # Save changes to the file
        await interaction.response.send_message(f'Warnings for {member.mention} have been cleared.')
    else:
        await interaction.response.send_message(f'{member.mention} has no warnings to clear.')


# Error handling for missing permissions
@warn.error
@view_warnings.error
@clear_warnings.error
async def permissions_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)


# The channel ID where applications will be sent
APPLICATION_CHANNEL_ID = 1297064864006537236  # Replace with your channel ID

# Time (in seconds) before the bot stops waiting for a response
TIMEOUT_DURATION = 60  

async def ask_question(interaction, question):
    """Helper function to ask a question and wait for a user's response."""
    await interaction.followup.send(question)

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await client.wait_for('message', check=check, timeout=TIMEOUT_DURATION)
        return msg.content
    except asyncio.TimeoutError:
        await interaction.followup.send("You took too long to respond!", ephemeral=True)
        return None

@client.tree.command(name="apply_mod", description="Apply for moderator role")
@app_commands.checks.has_permissions(administrator=True)
async def apply_mod(interaction: discord.Interaction):
    """Handles moderator application process with multiple questions."""
    await interaction.response.defer(ephemeral=True)

    # Ask first question
    question1 = "Why do you want to become a moderator?"
    response1 = await ask_question(interaction, question1)
    if response1 is None:
        return  # User did not respond in time

    # Ask second question
    question2 = "What experience do you have moderating other servers?"
    response2 = await ask_question(interaction, question2)
    if response2 is None:
        return

    # Ask third question
    question3 = "How many hours can you dedicate per week?"
    response3 = await ask_question(interaction, question3)
    if response3 is None:
        return

    # Ask fourth question
    question4 = "How do you handle conflict with other members in a team?"
    response4 = await ask_question(interaction, question4)
    if response4 is None:
        return

    # Ask fifth question
    question5 = "What would you do if you notice someone breaking the server rules?"
    response5 = await ask_question(interaction, question5)
    if response5 is None:
        return

    # Ask sixth question
    question6 = "Tell us about a time when you had to manage a difficult situation."
    response6 = await ask_question(interaction, question6)
    if response6 is None:
        return

    # Ask seventh question
    question7 = "Do you have any other commitments that might interfere with your ability to moderate?"
    response7 = await ask_question(interaction, question7)
    if response7 is None:
        return

    # If all questions were answered, send the application to the application channel
    application_channel = client.get_channel(APPLICATION_CHANNEL_ID)

    if application_channel is None:
        await interaction.followup.send("The application channel is not set up correctly.", ephemeral=True)
        return

    # Create an embed for the application
    embed = discord.Embed(title="New Moderator Application", color=discord.Color.blue())
    embed.add_field(name="Applicant", value=interaction.user.mention, inline=True)
    embed.add_field(name="Why do you want to become a moderator?", value=response1, inline=False)
    embed.add_field(name="Previous moderation experience?", value=response2, inline=False)
    embed.add_field(name="Weekly availability", value=response3, inline=False)
    embed.add_field(name="Handling team conflict?", value=response4, inline=False)
    embed.add_field(name="Action on rule-breaking?", value=response5, inline=False)
    embed.add_field(name="Difficult situation management?", value=response6, inline=False)
    embed.add_field(name="Other commitments?", value=response7, inline=False)
    embed.set_footer(text=f"Applied on: {interaction.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # Send the embed to the application channel
    await application_channel.send(embed=embed)
    await interaction.followup.send("Your application has been submitted!", ephemeral=True)

# Define the counting channel ID and initialize the current count
COUNTING_CHANNEL_ID = 1297083592815673344  # Replace with your actual channel ID
current_count = 0

# Event to handle counting in the specified channel
@client.event
async def on_message(message):
    global current_count
    
    if message.channel.id == COUNTING_CHANNEL_ID and not message.author.bot:
        try:
            # Try to parse the message content as an integer
            count = int(message.content)
            if count == current_count + 1:
                # If the count is correct, update the current count
                current_count = count
                client_message = await message.reply(f'✅ Correct! The current count is now {current_count}.')
                await asyncio.sleep(5)
                await client_message.delete()
            else:
                # If the count is incorrect, notify the user and optionally delete the message
                client_message = await message.reply(f'❌ Wrong count! The count should be {current_count + 1}.')
                await asyncio.sleep(5)
                await message.delete()
                await client_message.delete()
        except ValueError:
            # If the message is not a valid number, notify the user and optionally delete the message
            client_message = await message.reply('❌ Please enter a valid number.')
            await asyncio.sleep(5)
            await message.delete()
            await client_message.delete()
    # Ensure other commands still work
    await client.process_commands(message)

# Slash command to reset the count, restricted to users with manage_messages permission
@client.tree.command(name='reset', description='Reset the counting channel')
@app_commands.checks.has_permissions(manage_messages=True)
async def reset_count(interaction: discord.Interaction):
    global current_count
    current_count = 13
    await interaction.response.send_message('The counting has been reset!', ephemeral=True)

# Slash command to get the current count
@client.tree.command(name='count', description='Get the current count')
async def current_count_command(interaction: discord.Interaction):
    await interaction.response.send_message(f'The current count is {current_count}.', ephemeral=True)

 
client.run(TOKEN)
