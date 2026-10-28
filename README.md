# NAP10 Discord Bot

Python Discord bot with translation and three-person verification using SQLite.

## Translation

```text
! Hello, guys are you here? Spanish
! Hola chicos, ¿estáis aquí? English
! Bonjour tout le monde German
```

The last word is the target language. The bot replies once with a labeled translation embed. Languages include English, Spanish, German, French, Greek, Russian, Italian, Portuguese, Dutch, Polish, Turkish, Arabic, Japanese, Korean, Chinese and more. Translation uses deep-translator's unofficial Google Translate integration and requires internet access.

## Verification

New members receive the Verification Process role. The verification channel contains a **Start Verification** button, opening a modal asking for alliance and in-game username. The application appears in the review channel. Three **different users with the NAP10 role** must click Approve. The bot then gives the applicant the NAP10 role and removes Verification Process. Applications and approvals persist in SQLite.

## Installation

1. Install Python 3.11+ and create a Discord bot in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Enable **Server Members Intent** and **Message Content Intent** in the bot settings.
3. Invite the bot with `bot` and `applications.commands` scopes, granting View Channels, Send Messages, Embed Links, Read Message History and Manage Roles.
4. Place the bot's role **above** the NAP10 and Verification Process roles.
5. Run:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows use `.venv\\Scripts\\activate`. Enter your bot token in the private `.env` file. Never publish it.

6. Start using `python bot.py`.
7. Run `/setup_verification` **once** as a server administrator. This posts the persistent verification panel.

Restrict the voting channel to NAP10 reviewers and the bot. Configure channel permission overwrites so unverified members cannot access protected areas. The first three reviewers must receive the NAP10 role manually from an administrator.

## Configured server IDs

| Item | ID |
| --- | --- |
| Server | `1565084541289369690` |
| Vote channel | `1565096369100816424` |
| Process role | `1565092660690292767` |
| NAP10 role | `1565084866725413085` |
| Verification channel | `1565092827048845443` |

## Storage

SQLite is created automatically at `data/nap10.sqlite3`. Keep the `data/` directory on persistent storage when hosting the bot. The bot needs to be online to apply roles when members join and does not automatically repair joins missed while offline.
