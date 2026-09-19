import asyncio

import config
from logger_setup import setup_logger
from telegram_client import create_client, get_all_groups
from sender import send_to_group

logger = setup_logger()


async def run_broadcast():
    client = create_client()
    await client.start(phone=config.PHONE or None)

    logger.info("Logged in. Fetching dialogs...")
    groups = await get_all_groups(client)
    total = len(groups)
    logger.info(f"Found {total} eligible group(s) (excluding channels & private chats).")

    if total == 0:
        logger.info("No groups to message. Exiting.")
        await client.disconnect()
        return

    sent_count = 0
    skipped_count = 0

    for idx, dialog in enumerate(groups, start=1):
        logger.info(f"[{idx}/{total}] Processing group: {dialog.name}")

        success = await send_to_group(client, dialog, logger)

        if success:
            sent_count += 1
            if idx < total:
                logger.info(f"Waiting {config.DELAY_BETWEEN_SENDS}s before next group...")
                await asyncio.sleep(config.DELAY_BETWEEN_SENDS)
        else:
            skipped_count += 1
            # No wait on failure — move to next group immediately

    logger.info("=" * 50)
    logger.info(f"Broadcast finished. Sent: {sent_count} | Skipped: {skipped_count} | Total: {total}")
    logger.info("=" * 50)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_broadcast())
