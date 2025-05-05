# Discord Wiper Bot

An admin Discord bot for managing, purging, and auto-deleting messages across channels. Includes scheduled nukes, message backups, and an slash command help menu.

Quick Disclaimer:
This script will utilize the Discord Bot Token. Do NOT share this token, or any .env files that contain client secrets. 
You have been warned.

---

## Features

- `!wipe recent <count>` – Delete the last N messages
- `!wipe user @user <count>` – Delete messages from a specific user
- `!wipe channel` – Wipe the entire current channel
- `!wipeallchannels` – Wipe all text channels in the server
- `!autowipe <seconds>` – Automatically delete new messages after X seconds per channel
- `!nukeat HH:MM` – Schedule a full server wipe at a specified time (24-hour format)
- `!togglebackup` – Toggle whether message logs are backed up before deletion
- `/help` – Interactive slash command menu with dropdown and toggle buttons

---

## Backup System

- Before every wipe, up to 1000 messages are saved into a `.txt` file per channel
- Filenames follow the format:  
  `backup_<server_name>_<channel_name>.txt`
- Backups can be toggled on or off using `!togglebackup`

---

## Requirements

- Python 3.8+
- `discord.py` 2.3+  
  Install via:
    pip install -U discord.py


---

## Permissions

Ensure your bot has the following **bot permissions** when invited:

- View Channels  
- Send Messages  
- Manage Messages  
- Embed Links  
- Attach Files  
- Read Message History  
- Use Slash Commands  

For full functionality, you can enable Administrator perms but use only if you trust it.

---

## Setup & Running the Bot

1. Create a `.env` file in the root folder of your project:

```
DISCORD_TOKEN=your-bot-token-here
```

2. Run the bot, locally:

```bash
python wipe.py
```

---

## TODO

- Add support for channel deletion
- Add web dashboard for scheduling and monitoring
- Persist `autowipe` and `backup_enabled` settings across restarts

---

## Disclaimer

Use responsibly. This bot **deletes messages** and **modifies server content**. Always keep backups and restrict access to trusted users.
DO NOT EVER SHARE YOUR DISCORD BOT TOKEN!!!!
Enjoy wiping your servers.