from datetime import datetime
from pymongo.errors import *
from config import DATABASE_URL,DST_ID,FROM_MSG
import asyncio 
import logging
import pymongo

import pymongo.mongo_client
logging.basicConfig(
    format='[%(asctime)s] - [%(levelname)s] - %(message)s',
    level=logging.INFO
)
logging.getLogger("pymongo").setLevel(logging.ERROR)# SUPRESS "message": "Waiting for suitable server to become available"


#Variables
#===============#
collectionUri = DATABASE_URL
#===============#

#Things to do
'''
- update_channels - update vars
- 
'''

client = pymongo.MongoClient(collectionUri)
database = client.get_database('akumabot')
channels = database.get_collection('channels') 
if channels is None:
    channels = database['channels']


async def update_channels(source_id: int, from_msgid: int, to_msgid: int):
    try:
        date_time = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        update_channels = {
            "from_msg": from_msgid,
            "to_msg": to_msgid,
            "date_time":  date_time
        }
        update = {"$set": update_channels}
        query = {'src_id': source_id}        
        channels.update_one(query, update) 
            
    except Exception as error:
        logging.error(f"get_channel_info() : {error}") 

async def create_channel(source_id: int, channel_title):
        channel_info = {
        "title": channel_title,
        "src_id": source_id,
        "dst_id": DST_ID,
        "from_msg": FROM_MSG,
        "to_msg": None,
        "date_time":  None
        }
        channels.insert_one(channel_info)
        await get_channel_info(source_id, channel_title)
        
async def get_channel_info(source_id: int, channel_title: str):
    try:
        query = {'src_id': source_id}
        channel_exist = channels.count_documents(query)
        if channel_exist == 0:
            await create_channel(source_id, channel_title) 
        else:
            bot_vars = channels.find(query)
            for vars in bot_vars:
                dst_id = vars['dst_id']
                from_msg = vars['from_msg']
                to_msg = vars['to_msg']
            return dst_id, to_msg, from_msg
        return None
    except Exception as error:
        logging.error(f"get_channel_info() : {error}")
        
