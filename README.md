# NAP10 Discord Bot

Discord bot with simple translation and 3-person membership verification.

## Translation

Write the target language as the last word:

```text
! Könnt ihr bitte auf Bestätigen drücken? English
! Hello, guys, are you here? Spanish
```

The bot replies once with a clean translated embed. It uses the public MyMemory translation endpoint, not a Google account or API key. Language is detected locally with langdetect. The public endpoint has usage limits, may reject some language pairs and is not guaranteed to be online. Translation requests may be sent to MyMemory, so avoid private information. Messages are limited to 450 characters and an in-memory cache reduces repeat requests.

## Verification

A new member receives the Verification Process role. A persistent Start Verification button opens the alliance and in-game username form. Applications appear in the NAP10 review channel and need approval from three distinct NAP10 role holders. The bot assigns NAP10 and removes Verification Process only after three approvals. Failed role assignments can be retried by an existing approver without needing additional votes.

## Setup

1. Use Python 3.11+.
2. Create a Discord bot and enable Server Members Intent and Message Content Intent in the Discord Developer Portal.
3. Invite with bot and applications.commands scopes, granting View Channels, Send Messages, Embed Links, Read Message History and Manage Roles.
4. Make sure the bot role is above the NAP10 and Verification Process roles.
5. Run `pip install -r requirements.txt`.
6. Create `.env` (never upload it to GitHub) containing `DISCORD_TOKEN=your_actual_token`.
7. Set your hosting startup file to `bot.py` or rename `bot.py` to `main.py` on the host. Start with `python bot.py`.
8. As server administrator, run `/setup_verification` once in Discord.

The verification vote channel must only be visible to NAP10 reviewers and the bot. Configure channel permissions to block unverified members from protected areas.

## Discord IDs

| Purpose | ID |
| --- | --- |
| Server | 1565084541289369690 |
| Vote channel | 1565096369100816424 |
| Verification Process role | 1565092660690292767 |
| NAP10 role | 1565084866725413085 |
| Start Verification channel | 1565092827048845443 |

## Database

SQLite is automatically created at `data/nap10.sqlite3` and tracks applications and votes across restarts. Back up this file and use persistent hosting storage. The bot must be online to assign the pending role at join time. Three members need to have the NAP10 role before initial verification voting.
