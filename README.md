# Anonymous Support Bot

A production-ready Telegram bot for anonymous customer support, built with Python 3.11+, aiogram 3.x, and async SQLAlchemy.

## Features
- **Anonymous Messaging**: Users can send messages to the bot securely.
- **Multi-Agent Ticket System**: Support requests are broadcast to an admin group. Agents can "Claim" a ticket.
- **Private Routing**: Once claimed, sessions are handled privately in the DM of the claiming agent.
- **Media Support**: Supports forwarding of Text, Photos, Videos, Voice, Custom Stickers, and Documents.
- **Blocking System**: Integrated `/ban` command for abusive users.

## Setup Instructions

### 1. Requirements
Ensure you have Python 3.11+ installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
1. Rename `.env.example` to `.env`.
2. Add your Telegram Bot Token from BotFather.
3. Add the `ADMIN_GROUP_ID` (the numeric ID of the group where tickets will be broadcast). It should start with `-100`. To get it, add the bot to the group and use a userbot or debug bot.

### 4. Running Locally
Run the bot directly using Python:
```bash
python -m bot.main
```

### 5. Running with Docker (Recommended)
```bash
docker-compose up --build -d
```
