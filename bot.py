import asyncio
import logging
import os
import re
import sqlite3
from pathlib import Path

import discord
import aiohttp
from langdetect import detect, LangDetectException, DetectorFactory
DetectorFactory.seed = 0
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = 1565084541289369690
VOTE_CHANNEL_ID = 1565096369100816424
PROCESS_ROLE_ID = 1565092660690292767
NAP10_ROLE_ID = 1565084866725413085
VERIFY_CHANNEL_ID = 1565092827048845443
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/nap10.sqlite3"))
TOKEN = os.getenv("DISCORD_TOKEN", "")
MIN_APPROVALS = 3
COLOR = discord.Color.from_rgb(57, 113, 184)
LANGUAGES = {
    "english": "en", "spanish": "es", "german": "de", "french": "fr",
    "italian": "it", "portuguese": "pt", "russian": "ru", "greek": "el",
    "dutch": "nl", "polish": "pl", "turkish": "tr", "arabic": "ar",
    "japanese": "ja", "korean": "ko", "chinese": "zh-CN", "hindi": "hi",
    "ukrainian": "uk", "swedish": "sv", "norwegian": "no",
    "danish": "da", "finnish": "fi", "czech": "cs", "romanian": "ro"
}
log = logging.getLogger("nap10")


class Store:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS applications (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                alliance TEXT NOT NULL,
                username TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                message_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS votes (
                guild_id INTEGER NOT NULL,
                applicant_id INTEGER NOT NULL,
                voter_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, applicant_id, voter_id),
                FOREIGN KEY (guild_id, applicant_id)
                    REFERENCES applications (guild_id, user_id)
            );
        """)

    def application(self, guild_id, user_id):
        return self.conn.execute(
            "SELECT * FROM applications WHERE guild_id=? AND user_id=?",
            (guild_id, user_id)
        ).fetchone()

    def submit(self, guild_id, user_id, alliance, username):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            existing = self.application(guild_id, user_id)
            if existing and existing["status"] in ("pending", "approved"):
                self.conn.execute("COMMIT")
                return False
            self.conn.execute(
                """INSERT INTO applications(guild_id,user_id,alliance,username,status,message_id)
                   VALUES(?,?,?,?,'pending',NULL)
                   ON CONFLICT(guild_id,user_id) DO UPDATE SET
                   alliance=excluded.alliance,username=excluded.username,
                   status='pending',message_id=NULL,created_at=CURRENT_TIMESTAMP""",
                (guild_id, user_id, alliance, username)
            )
            self.conn.execute(
                "DELETE FROM votes WHERE guild_id=? AND applicant_id=?",
                (guild_id, user_id)
            )
            self.conn.execute("COMMIT")
            return True
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def set_message(self, guild_id, user_id, message_id):
        self.conn.execute(
            "UPDATE applications SET message_id=? WHERE guild_id=? AND user_id=?",
            (message_id, guild_id, user_id)
        )

    def count(self, guild_id, user_id):
        return self.conn.execute(
            "SELECT COUNT(*) FROM votes WHERE guild_id=? AND applicant_id=?",
            (guild_id, user_id)
        ).fetchone()[0]

    def vote(self, guild_id, applicant_id, voter_id):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            application = self.application(guild_id, applicant_id)
            if not application or application["status"] != "pending":
                self.conn.execute("COMMIT")
                return "closed", 0
            existing = self.conn.execute(
                "SELECT 1 FROM votes WHERE guild_id=? AND applicant_id=? AND voter_id=?",
                (guild_id, applicant_id, voter_id)
            ).fetchone()
            if existing:
                self.conn.execute("COMMIT")
                count = self.count(guild_id, applicant_id)
                return ("ready" if count >= MIN_APPROVALS else "duplicate"), count
            self.conn.execute(
                "INSERT INTO votes(guild_id,applicant_id,voter_id) VALUES(?,?,?)",
                (guild_id, applicant_id, voter_id)
            )
            number = self.count(guild_id, applicant_id)
            self.conn.execute("COMMIT")
            return "ready" if number >= MIN_APPROVALS else "recorded", number
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def mark_approved(self, guild_id, user_id):
        self.conn.execute("UPDATE applications SET status='approved' WHERE guild_id=? AND user_id=?", (guild_id, user_id))

    def cancel(self, guild_id, user_id):
        self.conn.execute("DELETE FROM votes WHERE guild_id=? AND applicant_id=?", (guild_id, user_id))
        self.conn.execute("DELETE FROM applications WHERE guild_id=? AND user_id=? AND status='pending'", (guild_id, user_id))

    def mark_pending(self, guild_id, user_id):
        self.conn.execute(
            "UPDATE applications SET status='pending' WHERE guild_id=? AND user_id=? AND status='approved'",
            (guild_id, user_id)
        )

    def pending(self):
        return self.conn.execute(
            "SELECT * FROM applications WHERE status='pending'"
        ).fetchall()

    def close(self):
        self.conn.close()


store = Store(DATABASE_PATH)


def make_embed(title, description=None, *, color=COLOR):
    return discord.Embed(title=title, description=description, color=color)


def vote_embed(member, application, approvals, status="pending"):
    embed = make_embed("NAP10 | Verification review")
    embed.add_field(name="Applicant", value=member.mention if member else f"<@{application['user_id']}>", inline=False)
    embed.add_field(name="Alliance", value=discord.utils.escape_markdown(application["alliance"]), inline=True)
    embed.add_field(name="In-game username", value=discord.utils.escape_markdown(application["username"]), inline=True)
    embed.add_field(name="Approvals", value=f"{approvals} / {MIN_APPROVALS}", inline=False)
    embed.set_footer(text="Approved" if status == "approved" else "NAP10 members only | One vote per person")
    return embed


class ApplicationModal(discord.ui.Modal, title="NAP10 Verification"):
    alliance = discord.ui.TextInput(label="What alliance are you from?", max_length=80, required=True)
    username = discord.ui.TextInput(label="What is your in-game username?", max_length=80, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        if not interaction.guild or interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("This verification is only available in the NAP10 server.", ephemeral=True)
        member = interaction.user
        if not isinstance(member, discord.Member):
            return await interaction.response.send_message("Member information unavailable. Please try again.", ephemeral=True)
        if member.get_role(NAP10_ROLE_ID):
            return await interaction.response.send_message("You are already verified.", ephemeral=True)
        existing = store.application(GUILD_ID, member.id)
        if existing and existing["status"] == "pending":
            return await interaction.response.send_message("Your verification is already awaiting review.", ephemeral=True)
        channel = interaction.guild.get_channel(VOTE_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("The review channel is not available. Contact an administrator.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            created = store.submit(GUILD_ID, member.id, str(self.alliance).strip(), str(self.username).strip())
            if not created:
                return await interaction.followup.send("You already have an active application.", ephemeral=True)
            application = store.application(GUILD_ID, member.id)
            message = await channel.send(embed=vote_embed(member, application, 0), view=VoteView(member.id), allowed_mentions=discord.AllowedMentions.none())
            store.set_message(GUILD_ID, member.id, message.id)
            await interaction.followup.send("Your application has been submitted. Three NAP10 approvals are required.", ephemeral=True)
        except discord.HTTPException:
            log.exception("Unable to create verification review")
            store.cancel(GUILD_ID, member.id)
            await interaction.followup.send("Could not post the application. Please try again.", ephemeral=True)
        except Exception:
            log.exception("Application submission failed")
            store.cancel(GUILD_ID, member.id)
            await interaction.followup.send("Verification failed. Please try again later.", ephemeral=True)


class StartVerification(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Start Verification", style=discord.ButtonStyle.primary, custom_id="nap10:start")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal())


class VoteView(discord.ui.View):
    def __init__(self, applicant_id: int):
        super().__init__(timeout=None)
        self.applicant_id = applicant_id
        self.add_item(VoteButton(applicant_id))


class VoteButton(discord.ui.Button):
    def __init__(self, applicant_id):
        super().__init__(label="Approve", style=discord.ButtonStyle.success, custom_id=f"nap10:approve:{applicant_id}")
        self.applicant_id = applicant_id

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild or interaction.guild.id != GUILD_ID:
            return await interaction.response.send_message("Invalid server.", ephemeral=True)
        if not isinstance(interaction.user, discord.Member) or not interaction.user.get_role(NAP10_ROLE_ID):
            return await interaction.response.send_message("Only verified NAP10 members may approve.", ephemeral=True)
        if interaction.user.id == self.applicant_id:
            return await interaction.response.send_message("You cannot approve yourself.", ephemeral=True)
        application = store.application(GUILD_ID, self.applicant_id)
        if not application or application["status"] != "pending" or application["message_id"] != interaction.message.id:
            return await interaction.response.send_message("This application is no longer open.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        state, number = store.vote(GUILD_ID, self.applicant_id, interaction.user.id)
        if state == "duplicate":
            return await interaction.followup.send("You already approved this applicant.", ephemeral=True)
        if state == "closed":
            return await interaction.followup.send("This application is already closed.", ephemeral=True)
        member = interaction.guild.get_member(self.applicant_id)
        if member is None:
            try:
                member = await interaction.guild.fetch_member(self.applicant_id)
            except discord.NotFound:
                member = None
        if state == "ready":
            role = interaction.guild.get_role(NAP10_ROLE_ID)
            process_role = interaction.guild.get_role(PROCESS_ROLE_ID)
            if not member or not role or not process_role:
                return await interaction.followup.send("Approval recorded, but roles could not be assigned. Contact an administrator.", ephemeral=True)
            try:
                await member.add_roles(role, reason="NAP10 verification: three approvals")
                await member.remove_roles(process_role, reason="NAP10 verification complete")
            except discord.HTTPException:
                store.mark_pending(GUILD_ID, self.applicant_id)
                log.exception("Unable to assign verification roles")
                return await interaction.followup.send("Approval recorded, but role assignment failed. Contact an administrator.", ephemeral=True)
        if state == "ready":
            store.mark_approved(GUILD_ID, self.applicant_id)
        try:
            await interaction.message.edit(
                embed=vote_embed(member, application, number, "approved" if state == "ready" else "pending"),
                view=None if state == "ready" else VoteView(self.applicant_id)
            )
        except discord.HTTPException:
            log.exception("Unable to update review embed")
        await interaction.followup.send(
            "Verification approved. NAP10 role granted." if state == "ready" else f"Approval recorded ({number}/{MIN_APPROVALS}).",
            ephemeral=True
        )


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user)


@bot.event
async def on_member_join(member):
    if member.guild.id != GUILD_ID or member.bot:
        return
    role = member.guild.get_role(PROCESS_ROLE_ID)
    if role:
        try:
            await member.add_roles(role, reason="Verification required")
        except discord.HTTPException:
            log.exception("Failed to assign process role")


TRANSLATION_CACHE = {}
TRANSLATION_LIMIT = asyncio.Semaphore(2)

async def translate_text(text, target):
    key = (text, target)
    if key in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[key]
    try:
        source = detect(text)
    except LangDetectException as exc:
        raise ValueError("Unable to identify input language") from exc
    source = {"zh-cn": "zh-CN", "zh-tw": "zh-TW"}.get(source.lower(), source)
    if source == target:
        return text
    async with TRANSLATION_LIMIT:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=18)) as session:
            async with session.get("https://api.mymemory.translated.net/get", params={"q": text, "langpair": f"{source}|{target}"}) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
    if payload.get("responseStatus") != 200:
        raise RuntimeError(str(payload.get("responseDetails") or "Provider rejected request"))
    translated = payload.get("responseData", {}).get("translatedText")
    if not translated:
        raise RuntimeError("Provider returned no text")
    if len(TRANSLATION_CACHE) >= 200:
        TRANSLATION_CACHE.pop(next(iter(TRANSLATION_CACHE)))
    TRANSLATION_CACHE[key] = translated
    return translated


@bot.event
async def on_message(message):
    if message.author.bot or not message.guild or message.guild.id != GUILD_ID:
        return
    match = re.fullmatch(r"!\\s*(.+?)\\s+([A-Za-z]+)", message.content.strip(), flags=re.DOTALL)
    if not match:
        return
    source_text, language_name = match.group(1).strip(), match.group(2).lower()
    target = LANGUAGES.get(language_name)
    if not target:
        return
    if len(source_text) > 450:
        return await message.reply("Maximum 450 characters per translation.", mention_author=False)
    try:
        translated = await translate_text(source_text, target)
        embed = make_embed(f"Translated to {language_name.title()}", discord.utils.escape_mentions(translated))
        embed.set_footer(text=f"Requested by {message.author.display_name}")
        await message.reply(embed=embed, mention_author=False, allowed_mentions=discord.AllowedMentions.none())
    except Exception:
        log.exception("Translation failed")
        await message.reply("Translation is temporarily unavailable or the free quota was reached.", mention_author=False)


@bot.tree.command(name="setup_verification", description="Post the NAP10 verification panel", guild=discord.Object(id=GUILD_ID))
@discord.app_commands.default_permissions(administrator=True)
async def setup_verification(interaction: discord.Interaction):
    if not interaction.guild or not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("Administrator access required.", ephemeral=True)
    channel = interaction.guild.get_channel(VERIFY_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message("Verification channel not found.", ephemeral=True)
    embed = make_embed("NAP10 | Member Verification", "Select **Start Verification** and submit your alliance and in-game username.\n\nAccess is granted after **3 NAP10 approvals**.")
    embed.set_footer(text="NAP10 Community | Verification")
    await channel.send(embed=embed, view=StartVerification())
    await interaction.response.send_message("Verification panel posted.", ephemeral=True)


@bot.event
async def setup_hook():
    bot.add_view(StartVerification())
    for application in store.pending():
        if application["guild_id"] == GUILD_ID and application["message_id"]:
            bot.add_view(VoteView(application["user_id"]), message_id=application["message_id"])
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if not TOKEN:
        raise SystemExit("Set DISCORD_TOKEN in your .env file")
    try:
        bot.run(TOKEN)
    finally:
        store.close()
