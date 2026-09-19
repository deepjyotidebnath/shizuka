from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import Chat, Channel
import config


def create_string_client(session_string: str = "") -> TelegramClient:
    """
    Client backed by an in-memory StringSession. No SQLite file is created,
    so there is nothing to lock and nothing on disk to be wiped.
    Pass "" to start a fresh (not yet logged-in) session.
    """
    return TelegramClient(StringSession(session_string), config.API_ID, config.API_HASH)


def create_client() -> TelegramClient:
    """
    Used by the CLI (broadcaster.py). Uses TG_SESSION if set, otherwise
    falls back to the old file-based session.
    """
    if config.SESSION_STRING:
        return create_string_client(config.SESSION_STRING)
    return TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)


def is_group(entity) -> bool:
    """
    Returns True only for actual GROUPS:
      - Basic (small) groups -> Chat instance
      - Megagroups / supergroups -> Channel instance with megagroup=True
    Excludes:
      - Broadcast channels (Channel with megagroup=False)
      - Private chats / users
    """
    if isinstance(entity, Chat):
        return True
    if isinstance(entity, Channel):
        return bool(getattr(entity, "megagroup", False))
    return False


async def get_all_groups(client: TelegramClient):
    groups = []
    async for dialog in client.iter_dialogs():
        if is_group(dialog.entity):
            groups.append(dialog)
    return groups
