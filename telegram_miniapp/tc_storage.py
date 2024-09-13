# tc_storage.py
import json
from typing import Dict, Any

from pytonconnect.storage import IStorage, DefaultStorage

async def get_filepath(chat_id: int) -> str:
    return f"wallet_storage/storage_{chat_id}.json"

async def get_storage_from_file(filename: str):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        return {}


async def write_storage_to_file(filename: str, data: Dict[Any, Any]):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


class TcStorage(IStorage):

    def __init__(self, chat_id: int):
        self.chat_id = chat_id

    def _get_key(self, key: str):
        return str(self.chat_id) + key

    async def set_item(self, key: str, value: str):
        storage = await get_storage_from_file(await get_filepath(self.chat_id))

        storage[self._get_key(key)] = value

        await write_storage_to_file(await get_filepath(self.chat_id), storage)

    async def get_item(self, key: str, default_value: str = None):
        storage = await get_storage_from_file(await get_filepath(self.chat_id))

        return storage.get(self._get_key(key), default_value)

    async def remove_item(self, key: str):
        storage = await get_storage_from_file(await get_filepath(self.chat_id))

        storage.pop(self._get_key(key))

        await write_storage_to_file(await get_filepath(self.chat_id), storage)
