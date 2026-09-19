from telethon.errors import (
    FloodWaitError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    ChatAdminRequiredError,
    SlowModeWaitError,
    ChannelPrivateError,
    ChatRestrictedError,
    UserDeactivatedBanError,
)
import config


async def send_to_group(client, dialog, logger, message=None) -> bool:
    """
    Attempt to send `message` (default: config.MESSAGE_TEXT) to a single group dialog.
    Returns True if the message was sent successfully, else False.
    Any Telegram API error results in a logged skip (never raises).
    """
    name = dialog.name or str(dialog.id)

    try:
        await client.send_message(dialog.entity, message if message is not None else config.MESSAGE_TEXT)
        logger.info(f"SENT -> '{name}' (id={dialog.id})")
        return True

    except FloodWaitError as e:
        logger.error(f"SKIP -> '{name}': flood wait, must wait {e.seconds}s")
    except SlowModeWaitError as e:
        logger.error(f"SKIP -> '{name}': slow mode active, wait {e.seconds}s")
    except ChatWriteForbiddenError:
        logger.error(f"SKIP -> '{name}': write permission forbidden")
    except ChatRestrictedError:
        logger.error(f"SKIP -> '{name}': chat is restricted")
    except UserBannedInChannelError:
        logger.error(f"SKIP -> '{name}': account banned in this group")
    except ChatAdminRequiredError:
        logger.error(f"SKIP -> '{name}': admin rights required")
    except ChannelPrivateError:
        logger.error(f"SKIP -> '{name}': group inaccessible / deleted")
    except UserDeactivatedBanError:
        logger.error(f"SKIP -> '{name}': account deactivated/banned by Telegram")
    except Exception as e:
        logger.error(f"SKIP -> '{name}': unexpected error: {e}")

    return False
