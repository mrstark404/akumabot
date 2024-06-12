import configparser
from dotenv import load_dotenv
from os import getenv


load_dotenv()

API_ID = int(getenv('API_ID'))
API_HASH = getenv('API_HASH')
DATABASE_URL = getenv('DATABASE_URL')
SESSION = getenv('STRING_SESSION')
SRC_ID = int(getenv('SRC_ID'))
DST_ID = int(getenv('DST_ID'))
FROM_MSG = int(getenv('FROM_MSG'))
BATCH_SIZE = int(getenv('BATCH_SIZE'))
MAX_ATTEMPTS = int(getenv('MAX_ATTEMPTS'))

if __name__ == '__main__':
    pass

