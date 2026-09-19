import asyncio
import hmac

import streamlit as st
from telethon.errors import AuthKeyUnregisteredError, SessionPasswordNeededError

import config
from telegram_client import create_string_client, get_all_groups
from sender import send_to_group

st.set_page_config(page_title="Telegram Group Broadcaster", page_icon="📨")
st.title("📨 Telegram Group Broadcaster")

# ---------------------------------------------------------------------------
# Optional password gate (set APP_PASSWORD in Secrets). Strongly recommended if
# TG_SESSION is stored in Secrets, because then anyone with the URL could send
# messages from your account.
# ---------------------------------------------------------------------------
if config.APP_PASSWORD and not st.session_state.get("pw_ok"):
    pw = st.text_input("App password", type="password")
    if pw:
        if hmac.compare_digest(pw, config.APP_PASSWORD):
            st.session_state.pw_ok = True
            st.rerun()
        else:
            st.error("Wrong password")
    st.stop()


# ---------------------------------------------------------------------------
# A tiny logger-like shim so sender.py's logger.info/error calls work and
# also show up in the Streamlit log panel.
# ---------------------------------------------------------------------------
class UILogger:
    def __init__(self, box):
        self.box = box
        self.lines = []

    def _add(self, msg):
        self.lines.append(msg)
        self.box.code("\n".join(self.lines[-200:]))

    def info(self, msg):
        self._add(f"INFO  {msg}")

    def error(self, msg):
        self._add(f"ERROR {msg}")


# ---------------------------------------------------------------------------
# Telegram helpers.
#
# Every helper opens its OWN short-lived client from a session *string*, does
# its work, and disconnects. Nothing is kept open between Streamlit reruns and
# there is no SQLite file, so there is nothing to lock and nothing to be
# deleted when the container recycles.
# ---------------------------------------------------------------------------
async def check_authorized(session_string: str) -> bool:
    client = create_string_client(session_string)
    await client.connect()
    try:
        return await client.is_user_authorized()
    finally:
        await client.disconnect()


async def send_code(phone: str):
    """Returns (session_string, phone_code_hash)."""
    client = create_string_client("")
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        return client.session.save(), sent.phone_code_hash
    finally:
        await client.disconnect()


async def submit_code(session_string: str, phone: str, code: str, code_hash: str):
    """Returns (session_string, needs_password)."""
    client = create_string_client(session_string)
    await client.connect()
    try:
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=code_hash)
            needs_password = False
        except SessionPasswordNeededError:
            needs_password = True
        return client.session.save(), needs_password
    finally:
        await client.disconnect()


async def submit_password(session_string: str, password: str) -> str:
    client = create_string_client(session_string)
    await client.connect()
    try:
        await client.sign_in(password=password)
        return client.session.save()
    finally:
        await client.disconnect()


async def run_broadcast(session_string, message, delay, status, progress_bar, logger):
    client = create_string_client(session_string)
    await client.connect()
    try:
        status.info("Fetching your groups...")
        groups = await get_all_groups(client)
        total = len(groups)
        logger.info(f"Found {total} eligible group(s).")

        if total == 0:
            status.warning("No groups found to message.")
            return 0, 0, 0

        sent = skipped = 0
        for idx, dialog in enumerate(groups, start=1):
            status.info(f"[{idx}/{total}] Sending to '{dialog.name}'...")
            success = await send_to_group(client, dialog, logger, message=message)
            if success:
                sent += 1
            else:
                skipped += 1
            progress_bar.progress(idx / total)
            if success and idx < total:
                await asyncio.sleep(delay)
        return sent, skipped, total
    finally:
        await client.disconnect()


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
ss = st.session_state
ss.setdefault("session_string", config.SESSION_STRING)  # "" = not logged in
ss.setdefault("stage", "form")                           # form -> code -> password
ss.setdefault("authorized", None)                        # None = not checked yet

if ss.authorized is None:
    if ss.session_string:
        with st.spinner("Checking Telegram login..."):
            try:
                ss.authorized = asyncio.run(check_authorized(ss.session_string))
            except Exception as e:
                st.error(f"Could not verify the saved login: {e}")
                ss.authorized = False
    else:
        ss.authorized = False

# ---------------------------------------------------------------------------
# Login flow (only when there's no valid session)
# ---------------------------------------------------------------------------
if not ss.authorized:
    st.info("Not logged in to Telegram — log in once below.")

    if ss.stage == "form":
        phone = st.text_input("Phone number (with country code)", value=config.PHONE or "")
        if st.button("Send login code"):
            try:
                ss.session_string, ss.code_hash = asyncio.run(send_code(phone))
                ss.phone = phone
                ss.stage = "code"
                st.rerun()
            except Exception as e:
                st.error(f"Failed to send code: {e}")

    elif ss.stage == "code":
        code = st.text_input("Enter the login code sent to your Telegram app")
        col1, col2 = st.columns(2)
        if col1.button("Submit code"):
            try:
                ss.session_string, needs_password = asyncio.run(
                    submit_code(ss.session_string, ss.phone, code, ss.code_hash)
                )
                if needs_password:
                    ss.stage = "password"
                else:
                    ss.authorized = True
                    ss.stage = "form"
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")
        if col2.button("Start over"):
            ss.session_string = config.SESSION_STRING
            ss.stage = "form"
            st.rerun()

    elif ss.stage == "password":
        pwd = st.text_input("Two-factor password", type="password")
        if st.button("Submit password"):
            try:
                ss.session_string = asyncio.run(submit_password(ss.session_string, pwd))
                ss.authorized = True
                ss.stage = "form"
                st.rerun()
            except Exception as e:
                st.error(f"Login failed: {e}")

else:
    st.success("Logged in to Telegram ✅")

    # If this login came from the browser (not from Secrets), offer the string
    # so it can be saved and reused after restarts.
    if ss.session_string and ss.session_string != config.SESSION_STRING:
        with st.expander("Stay logged in after restarts"):
            st.write(
                "This login only lives in this browser session. To keep it across "
                "restarts, add the value below to your app's Secrets as `TG_SESSION`. "
                "Treat it like a password: it gives full access to your Telegram account."
            )
            st.code(ss.session_string)

    message = st.text_area("Message to send", value=config.MESSAGE_TEXT, height=120)
    delay = st.number_input(
        "Delay between sends (seconds)", value=config.DELAY_BETWEEN_SENDS, min_value=0
    )

    if st.button("🚀 Start broadcast"):
        progress_bar = st.progress(0.0)
        status = st.empty()
        logger = UILogger(st.empty())

        try:
            sent, skipped, total = asyncio.run(
                run_broadcast(ss.session_string, message, delay, status, progress_bar, logger)
            )
            status.success(f"Done! Sent: {sent} | Skipped: {skipped} | Total: {total}")
        except AuthKeyUnregisteredError:
            # Session was revoked from Telegram → Settings → Devices
            ss.session_string = ""
            ss.authorized = False
            ss.stage = "form"
            st.error("This Telegram session was revoked. Please log in again.")
            st.rerun()
