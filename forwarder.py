#video duration filter added

from telethon import TelegramClient, errors , types
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.sync import TelegramClient,events
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

async def video_duration(client, channel_id,msg_id):
    try:
        message = await client.get_messages(channel_id, ids=msg_id)
        #video above 10 min
        media = message.media
        if hasattr(media, 'video'):
            return media.video.duration > 600
        elif hasattr(media, 'document'):
            return True
        else:
            return False
    except Exception as e:
        print("An error occurred while fetching video duration:", e)
        
async def source_msg_filter(client, channel_id):
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
                    if not is_gif(message):
                        filered_msg = await video_duration(client, source_id, from_msg) # filtering messages on the basis of duration
                        if filered_msg:
                            await client.send_message(destination_id, message)
                            await source_msg_filter(client,destination_id)
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

def is_gif(message):
    if isinstance(message.media, types.MessageMediaDocument):
        document = message.media.document
        if document.mime_type == 'image/gif':
            return True
        for attribute in document.attributes:
            if isinstance(attribute, types.DocumentAttributeAnimated):
                return True
    return False

async def getVars(source_id: int, channel_title: str) -> list[int]:
    try:
        vars = await get_channels(source_id, channel_title)
        if vars is not None:
            return [vars[0], vars[1]]
        else:
            return DST_ID, FROM_MSG
    except Exception as error:
        logging.error(f'getVars() : {error}')
    

async def main():
    try:
        #================#
        api_id = API_ID
        api_hash = API_HASH
        session = SESSION
        source_id = SRC_ID
        batch_size = BATCH_SIZE
        max_attempts = MAX_ATTEMPTS
        #=================#
        
        client = TelegramClient(StringSession(session), api_id, api_hash)
        message_queue = asyncio.Queue()
        async with client:
            try:
                
                await client.start()
                channel = await client.get_entity(SRC_ID)

                @client.on(events.NewMessage(chats=channel))
                async def handler(event):
                    await message_queue.put(event)

                async def message_processor():
                    while True:
                        event = await message_queue.get()
                        try:
                            vars = await getVars(SRC_ID, channel.title)
                            destination_id, from_msg = vars[0], vars[1]
                            to_msg = event.message.id
                            await asyncio.sleep(1) 
                            await forward_message(client, source_id, destination_id, to_msg, from_msg, batch_size, max_attempts)
                        except FloodWaitError as e:
                            logging.warning(f"Flood wait error: Waiting for {e.seconds} seconds")
                            await asyncio.sleep(e.seconds)
                        finally:
                            message_queue.task_done()

                # Start the message processor task
                asyncio.create_task(message_processor())

                logging.info(f"Monitoring new messages in channel: {SRC_ID}")
                await client.run_until_disconnected()

            except Exception as e:
                logging.error(f"An error occurred: {e}")
                await client.disconnect()
                
    except Exception as error:
        logging.error(f'main() : {error}')

if __name__ == '__main__':
    keep_alive()
    asyncio.run(main())
