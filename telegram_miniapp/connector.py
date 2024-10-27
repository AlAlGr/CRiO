import time

from pytonconnect import TonConnect

from telegram_miniapp.tc_storage import TcStorage
from base64 import urlsafe_b64encode

from pytoniq_core import begin_cell

MANIFEST_URL='https://raw.githubusercontent.com/AlAlGr/DgemWallet/main/manifest.json'

def get_connector(chat_id: int):
    return TonConnect(MANIFEST_URL, storage=TcStorage(chat_id))


def get_comment_message(destination_address: str, amount: int, comment: str) -> dict:

    data = {
        'address': destination_address,
        'amount': str(amount),
        'payload': urlsafe_b64encode(
            begin_cell()
            .store_uint(0, 32)  # op code for comment message
            .store_string(comment)  # store comment
            .end_cell()  # end cell
            .to_boc()  # convert it to boc
        )
        .decode()  # encode it to urlsafe base64
    }

    return data

async def send_transaction(user_id: int):
    connector = get_connector(user_id)
    connected = await connector.restore_connection()
    if not connected:
        return "Connect wallet first!"

    transaction = {
        'valid_until': int(time.time() + 3600),
        'messages': [
            get_comment_message(
                destination_address='0:0000000000000000000000000000000000000000000000000000000000000000',
                amount=int(0.01 * 10 ** 9),
                comment='hello world!'
            )
        ]
    }

    await connector.send_transaction(transaction)