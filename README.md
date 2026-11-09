# NAP10 Discord Bot

Discord bot with simple translation and 2-person membership verification.

## Translation

Write the target language as the last word:

```text
! Könnt ihr bitte auf Bestätigen drücken? English
! Hello, guys, are you here? Spanish
```

The bot replies once with a clean translated embed. It uses the public MyMemory translation endpoint, not a Google account or API key. Language is detected locally with langdetect. The public endpoint has usage limits, may reject some language pairs and is not guaranteed to be online. Translation requests may be sent to MyMemory, so avoid private information. Messages are limited to 450 characters and an in-memory cache reduces repeat requests.

## Verification

A new member receives the Verification Process role. A persistent Start Verification button opens the alliance and in-game username form. Applications appear in the NAP10 review channel and need approval from two distinct NAP10 role holders. The bot assigns NAP10 and removes Verification Process only after two approvals. Failed role assignments can be retried by an existing approver without needing additional votes.

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

SQLite is automatically created at `data/nap10.sqlite3` and tracks applications and votes across restarts. Back up this file and use persistent hosting storage. The bot must be online to assign the pending role at join time. Two members need to have the NAP10 role before initial verification voting.

## Controlled cross-server incident simulation

The operator keywords are accepted **only** in Discord server `1569493510715871232`, channel `1569493511286300775`. Commands must be sent by a server administrator. Set `INCIDENT_OPERATOR_USER_IDS` to a comma-separated list of operator Discord IDs for additional access restriction.

- `DataErrorRev.x`: publish a professional **simulated database connectivity incident** notice in **every text channel the bot can post to, across all servers where this bot is installed**.
- `FixDataError.x`: publish a short restoration notice in the same channels. After **60 seconds**, automatically remove **both** the original incident notices and restoration messages from those channels.

Notices are embeds without role or user mentions. Bot state and all message IDs are stored in `data/nap10_incidents.sqlite3` (override via `INCIDENT_DATABASE_PATH`), so cleanup continues after a bot restart. Repeated activation is blocked while an incident is active or its cleanup is pending. Channels without View Channel, Send Messages, Embed Links, or Read Message History access are skipped so all published notices remain eligible for automatic deletion. Notices use terse SRE-style terms such as **persistence-tier degradation**, **connection-pool saturation**, and **transaction commit latency**, with a discreet **MODE: CONTROLLED EXERCISE** field. The former footer is omitted entirely. The commands model an incident and do not verify that an actual database outage occurred.

The bot requires **Message Content Intent** in its code and **enabled under Discord Developer Portal → Bot → Privileged Gateway Intents** to detect text keywords. Both bot deployments must have access to the control server and channel. Keep `INCIDENT_DATABASE_PATH` on persistent storage and use only one running instance per bot to avoid conflicting broadcasts.

The keyword messages posted by the operator remain in the control channel as an audit trail. Short bot acknowledgements disappear automatically after 20 seconds. The two broadcast notices disappear after 60 seconds from recovery; they are removed only if they were posted by the same bot and match the stored incident template.
