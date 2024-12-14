from telethon.tl.types import DocumentAttributeFilename
from telethon.errors import FloodWaitError
import asyncio

delete_status_message = ""

async def delete_message(client, chat, query_msg_id, duplicate_msg_ids):
    chunk_size = 99  # Telegram API limit
    for i in range(0, len(duplicate_msg_ids), chunk_size):
        chunk = duplicate_msg_ids[i:i + chunk_size]
        try:
            await client.delete_messages(chat, chunk)
            print(f"ID {query_msg_id}: Deleted duplicate messages {chunk}")
            await asyncio.sleep(2)  # Short delay to avoid spam
        except FloodWaitError as e:
            print(f"Rate-limited! Sleeping for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            print(f"Error deleting messages {chunk}: {e}")

async def update_delete_status(current_msg_id, last_msg_id):
    if last_msg_id == 0:  # Avoid division by zero
        return
    
    progress = (current_msg_id / last_msg_id) * 100
    global delete_status_message
    
    delete_status_message = (
        f"Deletion Progress: {progress:.2f}%\n"
        f"Processed Message ID: {current_msg_id}\n"
        f"Last Message ID to Process: {last_msg_id}\n"
        f"Remaining Messages: {last_msg_id - current_msg_id}\n"
        f"{'-' * 50}"
    )

async def search_files(client, channel_id, first_msg_id):
    total_duplicate = 0
    last_message = await client.get_messages(channel_id, limit=1)
    last_msg_id = last_message[0].id if last_message else 0

    duplicate_msg_ids = []

    for msg_id in range(first_msg_id, last_msg_id):
        try:
            specific_message = await client.get_messages(channel_id, ids=msg_id)
            if not specific_message or not specific_message.message:
                continue

            # Extract file name from media
            query_file_name = None
            if specific_message.media and hasattr(specific_message.media, 'document'):
                for attribute in specific_message.media.document.attributes:
                    if isinstance(attribute, DocumentAttributeFilename):
                        query_file_name = attribute.file_name
                        break

            if not query_file_name:
                continue

            # Search for duplicates
            async for message in client.iter_messages(channel_id, search=query_file_name):
                if (
                    message.file and 
                    hasattr(message.file, 'name') and 
                    message.file.name == query_file_name and 
                    message.id != msg_id
                ):
                    duplicate_msg_ids.append(message.id)

            # Delete duplicates if found
            if duplicate_msg_ids:
                total_duplicate += len(duplicate_msg_ids)
                await delete_message(client, channel_id, msg_id, duplicate_msg_ids)
                duplicate_msg_ids = []  # Reset after deletion
                await asyncio.sleep(3)  # Delay between batches

        except FloodWaitError as e:
            print(f"Rate-limited! Sleeping for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds + 1)
        except Exception as e:
            print(f"Error processing message ID {msg_id}: {e}")
        
        # Update progress
        await update_delete_status(msg_id, last_msg_id)
        await asyncio.sleep(1)

    return f"Total Duplicate Messages Deleted: {total_duplicate}"
