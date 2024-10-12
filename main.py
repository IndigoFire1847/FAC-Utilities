import discord
import os
import sys
import json
import random
from datetime import datetime

from discord import app_commands
from discord.ext import commands, tasks

intents = discord.Intents.default()
intents.message_content = True

OWNER_ID = # insert your own discord user id here

client = commands.Bot(command_prefix='-', intents=intents)

@client.event
async def on_ready():
  print("ready")
  periodic_save.start()
  try:
    synced = await client.tree.sync()
    print(f"synced {len(synced)} command(s)")
  except Exception as e:
    print(e)

# File where levels and XP are stored. Change role names and level requirement as needed
LEVEL_FILE = 'levels.json'
ROLE_LEVELS = {
  5: "Level 5",
  10:"Level 10",
  15: "Level 15",
}

# Load or create the levels JSON file
def load_levels():
    try:
        with open(LEVEL_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_levels(level_data):
    with open(LEVEL_FILE, 'w') as f:
        json.dump(level_data, f, indent=4)

# Load existing levels and XP
levels = load_levels()

# Utility function to calculate level based on XP
def calculate_level(xp):
    return int((xp // 100) ** 0.5)

# Add XP to a user
def add_xp(user_id, xp_amount):
    user_id = str(user_id)

    # Create a new entry if the user doesn't have one
    if user_id not in levels:
        levels[user_id] = {'xp': 0, 'level': 1}

    # Add XP
    levels[user_id]['xp'] += xp_amount
    new_level = calculate_level(levels[user_id]['xp'])

    # Check for level up
    if new_level > levels[user_id]['level']:
        levels[user_id]['level'] = new_level
        return new_level  # Return the new level to indicate the user leveled up

    save_levels(levels)
    return None  # No level up

# Cooldown to prevent spamming for XP
@client.event
async def on_message(message):
    if message.author.bot:
        return  # Ignore bot messages

    xp_to_add = random.randint(15, 25)  # Random XP for each message
    leveled_up = add_xp(message.author.id, xp_to_add)

    if leveled_up:
        await message.channel.send(f"🎉 {message.author.mention} leveled up to level {leveled_up}!")

    await client.process_commands(message)

# Function to check and assign roles based on level
async def check_and_assign_role(user, level, guild):
    # Check if the user has hit a level that requires a role
    for role_level, role_name in ROLE_LEVELS.items():
        if level == role_level:
            # Find the role in the guild by name
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role not in user.roles:
                await user.add_roles(role)
                await user.send(f"Congratulations! You've been assigned the role **{role_name}** for reaching level {level}!")
                return  # Role assigned, exit function

# Command for checking a user's level and XP
@client.tree.command(name="level", description="Check your level and XP")
async def level(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    user_id = str(member.id)

    if user_id in levels:
        xp = levels[user_id]['xp']
        level = levels[user_id]['level']
        await interaction.response.send_message(f"{member.display_name} is currently level {level} with {xp} XP.")
    else:
        await interaction.response.send_message(f"{member.display_name} has no XP yet.")

# Command for displaying a leaderboard of top users by level
@client.tree.command(name="leaderboard", description="Display the top 10 users by level")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(levels.items(), key=lambda x: x[1]['xp'], reverse=True)[:10]  # Top 10 users
    leaderboard_text = "\n".join([f"<@{user_id}>: Level {data['level']} ({data['xp']} XP)" for user_id, data in sorted_users])

    embed = discord.Embed(title="🏆 Leaderboard", description=leaderboard_text, color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

# Command to reset a user's level (Admin only)
@client.tree.command(name="reset_level", description="Reset a user's level")
@app_commands.checks.has_permissions(administrator=True)
async def reset_level(interaction: discord.Interaction, member: discord.Member):
    user_id = str(member.id)
    if user_id in levels:
        del levels[user_id]
        save_levels(levels)
        await interaction.response.send_message(f"{member.display_name}'s level has been reset.")
    else:
        await interaction.response.send_message(f"{member.display_name} has no XP to reset.")

# Command to manually add XP to a user (Admin only)
@client.tree.command(name="addxp", description="Manually add XP to a user")
@app_commands.checks.has_permissions(administrator=True)
async def addxp(interaction: discord.Interaction, member: discord.Member, xp: int):
    leveled_up = add_xp(member.id, xp)
    await interaction.response.send_message(f"Added {xp} XP to {member.display_name}.")

    if leveled_up:
        await interaction.followup.send(f"🎉 {member.mention} leveled up to level {leveled_up}!")

# Save levels periodically
@tasks.loop(minutes=10)
async def periodic_save():
    save_levels(levels)

# Define the ID of the logging channel
LOGGING_CHANNEL_ID = 1292447543091007550  # Replace with the actual ID of your logging channel

# Utility function to get the logging channel
async def get_logging_channel(guild):
    return discord.utils.get(guild.text_channels, id=LOGGING_CHANNEL_ID)

# EVENT LISTENERS 

# Log message deletions
@client.event
async def on_message_delete(message):
    if message.guild:
        log_channel = await get_logging_channel(message.guild)
        if log_channel:
            embed = discord.Embed(
                title="Message Deleted",
                description=f"Message by {message.author.mention} in {message.channel.mention} was deleted.",
                color=discord.Color.red()
            )
            embed.add_field(name="Content", value=message.content or "No content", inline=False)
            embed.set_footer(text=f"User ID: {message.author.id} | Message ID: {message.id}")
            await log_channel.send(embed=embed)

# Log message edits
@client.event
async def on_message_edit(before, after):
    if before.guild:
        log_channel = await get_logging_channel(before.guild)
        if log_channel and before.content != after.content:
            embed = discord.Embed(
                title="Message Edited",
                description=f"Message by {before.author.mention} in {before.channel.mention} was edited.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Before", value=before.content or "No content", inline=False)
            embed.add_field(name="After", value=after.content or "No content", inline=False)
            embed.set_footer(text=f"User ID: {before.author.id} | Message ID: {before.id}")
            await log_channel.send(embed=embed)

# Log member join
@client.event
async def on_member_join(member):
    log_channel = await get_logging_channel(member.guild)
    if log_channel:
        embed = discord.Embed(
            title="Member Joined",
            description=f"{member.mention} has joined the server.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"User ID: {member.id}")
        await log_channel.send(embed=embed)

# Log member leave
@client.event
async def on_member_remove(member):
    log_channel = await get_logging_channel(member.guild)
    if log_channel:
        embed = discord.Embed(
            title="Member Left",
            description=f"{member.mention} has left the server.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"User ID: {member.id}")
        await log_channel.send(embed=embed)

# Log member bans
@client.event
async def on_member_ban(guild, member):
    log_channel = await get_logging_channel(guild)
    if log_channel:
        embed = discord.Embed(
            title="Member Banned",
            description=f"{member.mention} was banned from the server.",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"User ID: {member.id}")
        await log_channel.send(embed=embed)

# Log member unbans
@client.event
async def on_member_unban(guild, user):
    log_channel = await get_logging_channel(guild)
    if log_channel:
        embed = discord.Embed(
            title="Member Unbanned",
            description=f"{user.mention} was unbanned from the server.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"User ID: {user.id}")
        await log_channel.send(embed=embed)

# Log role updates
@client.event
async def on_member_update(before, after):
    if before.guild:
        log_channel = await get_logging_channel(before.guild)
        if log_channel:
            if before.roles != after.roles:
                embed = discord.Embed(
                    title="Roles Updated",
                    description=f"{before.mention}'s roles were updated.",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Before", value=", ".join([role.name for role in before.roles]), inline=False)
                embed.add_field(name="After", value=", ".join([role.name for role in after.roles]), inline=False)
                embed.set_footer(text=f"User ID: {before.id}")
                await log_channel.send(embed=embed)

# Log channel creation
@client.event
async def on_guild_channel_create(channel):
    log_channel = await get_logging_channel(channel.guild)
    if log_channel:
        embed = discord.Embed(
            title="Channel Created",
            description=f"A new channel {channel.mention} was created.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await log_channel.send(embed=embed)

# Log channel deletion
@client.event
async def on_guild_channel_delete(channel):
    log_channel = await get_logging_channel(channel.guild)
    if log_channel:
        embed = discord.Embed(
            title="Channel Deleted",
            description=f"The channel {channel.name} was deleted.",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await log_channel.send(embed=embed)

# Log channel updates
@client.event
async def on_guild_channel_update(before, after):
    log_channel = await get_logging_channel(before.guild)
    if log_channel:
        embed = discord.Embed(
            title="Channel Updated",
            description=f"The channel {before.mention} was updated.",
            color=discord.Color.blue()
        )
        if before.name != after.name:
            embed.add_field(name="Old Name", value=before.name, inline=False)
            embed.add_field(name="New Name", value=after.name, inline=False)
        await log_channel.send(embed=embed)

# Ping Command

@client.tree.command(description="gets the bots ping!")
async def ping(interaction: discord.Interaction):
    embed = discord.Embed(title="ARL Bot ping")
    embed.add_field(name="Bot ping", value=f"{round(client.latency * 1000)}ms")
    await interaction.response.send_message(embed=embed, ephemeral = True)

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

# User info Command

@client.tree.command(description = "get the info of a user")
@app_commands.describe(member = "Which user am i getting the info for?")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
        embed = discord.Embed(title=f"Userinfo for {member.name}", 
              description=f"this is the user info for {member.mention}")
        embed.add_field(name="joined server at:",
                        value=member.joined_at.strftime("%d/%m/%y, %H:%M:%S")
                        if member.joined_at else "Not available")
        embed.add_field(name="joined discord at:", 
                        value=member.created_at.strftime("%d/%m/%y, %H:%M:%S"))
        embed.add_field(name="User ID",
                        value= f"their id is {member.id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

# Warn command (is a moderation command)

@app_commands.describe(user = "who should i warn?", reason = "Why am i warning them?")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, user: discord.User, reason: str):
    await interaction.response.send_message(f'I have warned {user} with the reason' 
    f' {reason}', ephemeral = True)
    await user.send(f"you were warned in FAC for {reason}")

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
    await interaction.response.send_message(f"Cleared {amount} messages!"
                                            , ephemeral=True)
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

# Error handler for slowmode command in case permissions are missing
@slowmode.error
async def slowmode_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

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
  await interaction.response.send_message("The link to my source code is here: 

# Handler for poll command if user doesn't have permissions

@poll.error
async def poll_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)

# Kick command handler if user doesn't have permissions

@kick.error
async def kick_error(interaction: discord.Interaction, error):
  if isinstance(error, app_commands.error.MissingPermissions):
    await interaction.response.send_message("You don't have permission to kick users", ephemeral = True)

# Ban command handler if user doesn't have permissions

@ban.error
async def ban_error(interaction: discord.Interaction, error):
  if isinstance(error, app_commands.error.MissingPermissions):
    await interaction.response.send_message("You don't have permission to ban users", ephemeral = True)

# Unban handler if user doesn't have permissions

@unban.error
async def unban_error(interaction: discord.Interaction, error):
  if isinstance(error, app_commands.error.MissingPermissions):
    await interaction.response.send_message("You don't have permission to unban users", ephemeral = True)

# Warn handler if user doesn't have permission

@warn.error
async def warn_error(interaction: discord.Interaction, error):
  if isinstance(error, app_commands.error.MissingPermissions):
    await interaction.response.send_message("You don't have permission to warn users", ephemeral = True)


client.run(Your Token Here)
