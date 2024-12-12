from telethon import TelegramClient, errors , types
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.sync import TelegramClient,events
from telethon.tl.types import MessageMediaDocument, DocumentAttributeVideo
from db import *
from config import *
import asyncio
import logging
import re
from alive import keep_alive

logging.basicConfig(
    format='[%(asctime)s] - %(levelname)s - %(message)s',
    level=logging.INFO

)

#================#
api_id = API_ID
api_hash = API_HASH
session = SESSION
source_id = SRC_ID
batch_size = BATCH_SIZE
max_attempts = MAX_ATTEMPTS
#=================#

async def rename(msg_caption):
    filter_msgs = [
        'JOIN & SUPPORT | @Eliteflix_Official',
        '🤍Join and Support @RebornFlix',
        'Join  @RebornFlix ✅',
        '✅Join and Support : @RebornFlix',
        '❕Join and Support : @RebornFlix',
        '''None
❕Join and Support : @RebornFlix'''

    ]
    pattern = '|'.join(re.escape(msg) for msg in filter_msgs)
    regex = re.compile(pattern)
    renamed_msg = regex.sub('', msg_caption).strip()
    return renamed_msg

def get_video_duration(message):
    # Check if the message has media and it's a document
    if isinstance(message.media, MessageMediaDocument):
        # Access the document's attributes
        for attribute in message.media.document.attributes:
            if isinstance(attribute, DocumentAttributeVideo):
                # Return the duration
                return attribute.duration
    return None

async def filter_media_file(client, channel_id,msg_id):
    try:
        message = await client.get_messages(channel_id, ids=msg_id)
        duration_in_seconds = get_video_duration(message)
        
        if duration_in_seconds:
            return duration_in_seconds > 600
        
        elif message.media.document.size:
            size_in_bytes = message.media.document.size
            size_in_mb = size_in_bytes / (1024 * 1024)
            return int(size_in_mb) > 30
        
        else:
            return False
        
    except Exception as e:
        print("An error occurred while fetching video duration:", e)
        
async def rename_media_file(client, channel_id):
    async for message in client.iter_messages(channel_id):
        try:
            if message.media and isinstance(message.media, types.MessageMediaDocument):
                document = message.media.document
                if document.mime_type == 'image/webp' and any(isinstance(attribute, types.DocumentAttributeSticker) for attribute in document.attributes):
                    continue  # Skip processing stickers
            formatted_msg = await rename(message.text)
            if formatted_msg != message.text:
                await client.edit_message(channel_id, message.id, formatted_msg)
        except errors.FloodWaitError as e:
            logging.warning(f"FloodWait: Sleeping for {e.seconds} seconds.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logging.error(f"source_msg_filter() : {e}")
        finally:
            break 
         
def is_sticker(message):
    if isinstance(message.media, types.MessageMediaDocument):
        document = message.media.document
        if document.mime_type in {'image/gif', 'application/pdf'}:
            return True
        
        for attribute in document.attributes:
            if isinstance(attribute, types.DocumentAttributeAnimated):
                return True
    return False



async def forward_message(client, source_id, destination_id, to_msg, from_msg, batch_msg, max_attempts):
    try:
        if from_msg == 0:
            from_msg = 1
            
        attempts = 0
        from_msg += 1
        ismaxattempt = False
        found_media = False
        while from_msg <= to_msg:
            messages_to_send = min(batch_msg, to_msg - from_msg + 1)
            delay = messages_to_send
            if ismaxattempt == True:
                break
            
            for _ in range(messages_to_send):
                message = await client.get_messages(source_id, ids=from_msg)
                if message and message.media:
                    if not is_sticker(message):
                        # filtering messages on the basis of duration
                        filered_msg = await filter_media_file(client, source_id, from_msg) 
                        if filered_msg:
                            await client.send_message(destination_id, message)
                            await rename_media_file(client, destination_id)
                            found_media = True
                            attempts = 0  # Reset attempts when a media message is found
                else:
                    # logging.info(f"Skipping non-media message with ID: {from_msg}")
                    attempts += 1
                    if attempts >= max_attempts:
                        logging.info(f"Reached maximum attempts ({max_attempts})")
                        ismaxattempt = True
                        break
                    
                last_msg_id = from_msg
                from_msg += 1
                
            logging.info(f"Message has been forwarded up to ID: {from_msg}") #Batch message sent
            
            if found_media:
                await update_channels(source_id, last_msg_id, to_msg)
                
            logging.info(f"Sleeping for {delay} seconds.")
            await asyncio.sleep(delay)
            
    except errors.FloodWaitError as e:
        logging.warning(f"FloodWait: Sleeping for {e.seconds} seconds.")
        await asyncio.sleep(e.seconds)
        
    except Exception as error:
        logging.error(f"forward_message() : {error}")


async def getVars(source_id: int, channel_title: str) -> tuple[int, int, int]:
    try:
        vars = await get_channel_info(source_id, channel_title)
        if vars:
            return vars
        
        return DST_ID, FROM_MSG
    except Exception as error:
        logging.error(f"Error in {getVars.__name__}: {str(error)}")


async def main():
    try:
        # Initialize Telegram client
        client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
        latest_message_queue = asyncio.Queue(maxsize=1)

        async with client:
            await client.start()

            # Fetch channel details
            source_channel = await client.get_entity(SRC_ID)
            destination_channel = await client.get_entity(DST_ID)
            logging.info(f"Source: {source_channel.title}, Destination: {destination_channel.title}")

            destination_id, from_msg = await getVars(SRC_ID, source_channel.title)


            # Event handler for new messages
            @client.on(events.NewMessage(chats=source_channel))
            async def handle_new_message(event):
                try:
                    # Clear queue to keep only the latest message
                    while not latest_message_queue.empty():
                        latest_message_queue.get_nowait()

                    # Add the latest message to the queue
                    await latest_message_queue.put(event)
                    logging.info(f"New message queued: {event.message.id}")
                except Exception as e:
                    logging.error(f"Error in handle_new_message: {str(e)}")

            # Process queued messages
            async def process_messages():
                while True:
                    event = await latest_message_queue.get()
                    try:
                        latest_msg_id = event.message.id
                        logging.info(f"Processing latest message ID: {latest_msg_id}")

                        await forward_message(
                            client, SRC_ID, destination_id, latest_msg_id, from_msg, BATCH_SIZE, MAX_ATTEMPTS
                        )
                    except errors.FloodWaitError as e:
                        logging.warning(f"FloodWaitError: Sleeping for {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        logging.error(f"Error in process_messages: {str(e)}")
                    finally:
                        latest_message_queue.task_done()

            # Sync database periodically
            async def sync_database():
                while True:
                    try:
                        nonlocal destination_id, from_msg
                        to_msg = FROM_MSG + 10
                        latest_message = await client.get_messages(source_id, limit=1)
                        if latest_message:
                            to_msg = latest_message[0].id 
                        if from_msg < to_msg:
                            logging.info(f"Syncing messages from {from_msg} to {to_msg}...")
                            await forward_message(
                                client, SRC_ID, destination_id, to_msg, from_msg, BATCH_SIZE, MAX_ATTEMPTS
                            )

                            # Update message variables
                            destination_id, to_msg, from_msg = await getVars(SRC_ID, source_channel.title)
                    except errors.FloodWaitError as e:
                        logging.warning(f"FloodWaitError during sync: Sleeping for {e.seconds} seconds")
                        await asyncio.sleep(e.seconds)
                    except Exception as e:
                        logging.error(f"Error in sync_database: {str(e)}")
                    finally:
                        await asyncio.sleep(3600)  # Sleep for 2 hours before the next sync

            # Start tasks
            asyncio.create_task(process_messages())
            asyncio.create_task(sync_database())

            # Keep client running
            await client.run_until_disconnected()

    except Exception as error:
        logging.error(f"Error in main(): {str(error)}")

if __name__ == '__main__':
    keep_alive()
    asyncio.run(main())
