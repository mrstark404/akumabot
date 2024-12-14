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
    if isinstance(message.media, MessageMediaDocument):
        for attribute in message.media.document.attributes:
            if isinstance(attribute, DocumentAttributeVideo):
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
            formatted_msg = await rename(message.text)
            if formatted_msg != message.text:
                await client.edit_message(channel_id, message.id, formatted_msg)
        except errors.FloodWaitError as e:
            logging.warning(f"Rename FloodWait: Sleeping for {e.seconds} seconds.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            logging.error(f"{rename_media_file.__name__} : {str(e)}")
        finally:
            break 
         
def is_not_sticker(message):
    if isinstance(message.media, types.MessageMediaDocument):
        document = message.media.document
        if document.mime_type in {'image/gif', 'application/pdf', 'image/webp'}:
            return False
        
        for attribute in document.attributes:
            if isinstance(attribute, types.DocumentAttributeAnimated):
                return False
    return True


async def single_forward(client, source_id, destination_id, msg_id):
    message = await client.get_messages(source_id, ids=msg_id)
    if message and message.media:
        if is_not_sticker(message):
            filered_msg = await filter_media_file(client, source_id, msg_id) 
            if filered_msg:
                await client.send_message(destination_id, message)
                await rename_media_file(client, destination_id)        
                return True
    return False

async def batch_forward(client, source_id, destination_id, from_msg, to_msg, batch_msg, max_attempts):
    try:
        if from_msg == 0:
            from_msg = 1
            
        attempts = 0
        from_msg += 1
        is_max_attempt = False
        found_media = False
        while from_msg <= to_msg:
            messages_to_send = min(batch_msg, to_msg - from_msg + 1)
            delay = messages_to_send
            if is_max_attempt == True:
                break
            
            for _ in range(messages_to_send):
                message = await client.get_messages(source_id, ids=from_msg)
                
                if await single_forward(client, source_id, destination_id, from_msg):
                    attempts = 0  
                else:
                    attempts += 1
                    if attempts >= max_attempts:
                        logging.info(f"Reached maximum attempts ({max_attempts})")
                        is_max_attempt = True
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
        logging.error(f"{batch_forward.__name__} : {error}")



# Main function to start both client and bot concurrently
async def main():
    try:
        client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)
        bot = TelegramClient('forward_bot', API_ID, API_HASH)
        
        
        await client.start()
        await bot.start(bot_token=BOT_TOKEN)
        state = {
        'from_channel': None,
        'to_channel': None,
        'from_message': None,
        'to_message': None
    }



        async def fetch_channels():
            source_channel = await client.get_entity(SRC_ID)
            destination_channel = await client.get_entity(DST_ID)
            logging.info(f"Source: {source_channel.title}, Destination: {destination_channel.title}")
            return source_channel, destination_channel

        @client.on(events.NewMessage(chats=SRC_ID))
        async def handle_new_message(event):
            try:
                msg_id = event.message.id
                await single_forward(client, SRC_ID, DST_ID, msg_id)
            except Exception as e:
                logging.error(f"Error in handle_new_message: {str(e)}")

        @bot.on(events.NewMessage(pattern='/from_channel'))
        async def var_from_channel(event):
            text = " ".join(event.message.text.split()[1:])
            if text.startswith("-100"):
                state['from_channel'] = text
                await event.reply(f"from_channel set to: {state['from_channel']}")

        @bot.on(events.NewMessage(pattern='/to_channel'))
        async def var_to_channel(event):
            text = " ".join(event.message.text.split()[1:])
            if text.startswith("-100"):
                state['to_channel'] = text
                await event.reply(f"to_channel set to: {state['to_channel']}")

        @bot.on(events.NewMessage(pattern='/from_message'))
        async def var_from_message(event):
            text = " ".join(event.message.text.split()[1:])
            state['from_message'] = text
            await event.reply(f"from_message set to: {state['from_message']}")

        @bot.on(events.NewMessage(pattern='/to_message'))
        async def var_to_message(event):
            text = " ".join(event.message.text.split()[1:])
            state['to_message'] = text
            await event.reply(f"to_message set to: {state['to_message']}")

        # Bot command to show current status
        @bot.on(events.NewMessage(pattern='/status'))
        async def bot_status(event):
            status_msg = f"BOT STATUS\n\nfrom_channel: {state['from_channel']}\nto_channel: {state['to_channel']}\nfrom_message: {state['from_message']}\nto_message: {state['to_message']}"

            await event.reply(status_msg)

        # Bot command to start batch forwarding
        @bot.on(events.NewMessage(pattern='/start_forward'))
        async def start_batch_forward(event):
            global batch_task
            
            if state['from_channel'] and state['to_channel']:
                from_channel = int(state['from_channel'])
                to_channel = int(state['to_channel'])
                from_message = int(state['from_message'])
                to_message = int(state['to_message'])
                
                batch_task = asyncio.create_task(batch_forward(
                    client, 
                    from_channel,
                    to_channel, 
                    from_message,
                    to_message,
                    BATCH_SIZE,
                    MAX_ATTEMPTS
                ))
                
                await event.reply("Batch forward started.")               
                await batch_task
                await event.reply(f"Forward completed upto {to_message}")               
                
            else:
                await event.reply("Set variables from_channel, to_channel first.")

        # Bot command to stop batch forwarding
        @bot.on(events.NewMessage(pattern='/stop_forward'))
        async def stop_batch_forward(event):
            global batch_task
            if batch_task and not batch_task.done():
                batch_task.cancel()
                try:
                    await batch_task
                except asyncio.CancelledError:
                    await event.reply("Task has been cancelled successfully.")
            else:
                await event.reply("No active task to cancel.")

        # Bot command to check bot's status
        @bot.on(events.NewMessage(pattern='/ping'))
        async def bot_handler(event):
            await event.reply("Bot is running.")
        
        try:
            await client.run_until_disconnected()
            await bot.run_until_disconnected()
        except asyncio.CancelledError:
            pass  # Handle cancellation gracefully

        await client.disconnect()
        await bot.disconnect()
            
    except Exception as e:
        logging.error(f"{main.__name__}: {str(e)}")


if __name__ == '__main__':
    keep_alive()
    asyncio.run(main())
