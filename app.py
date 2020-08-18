from binance.client import Client
from os import environ
from decimal import Decimal
import logging
import asyncio
import uvloop
import aio_pika
import ujson
import httpx


API_KEY = environ.get('API_KEY')
API_SECRET = environ.get('API_SECRET')
PAIR = environ.get('PAIR')
AMQP_CONN_STRING = environ.get('AMQP_CONN_STRING')
AMQP_QUEUE = environ.get('AMQP_QUEUE')
STOP_DELTA = environ.get('STOP_DELTA')
TP_DELTA = environ.get('TP_DELTA')
SELL_NOTIFICATION_ENDPOINT = environ.get('SELL_NOTIFICATION_ENDPOINT')
PRECISIONS = {
    'BTCUSDT': 6
}
LAST_CLOSE = 0.0

uvloop.install()


class logger():
    pass


logger.info = print


def get_binance_client() -> Client:
    client = Client(api_key=API_KEY,
                    api_secret=API_SECRET)
    return client


async def ticker():
    global LAST_CLOSE
    logger.info('Starting to get ticker feed')
    while True:
        client = get_binance_client()
        LAST_CLOSE = Decimal(client.get_ticker(symbol=PAIR).get('lastPrice'))
        await asyncio.sleep(1)


async def monitor_price(stop_price, tp_price):
    global LAST_CLOSE
    logger.info(f'Monitoring price between {stop_price} and {tp_price}')
    while stop_price < LAST_CLOSE < tp_price:
        await asyncio.sleep(0.05)


def format_number(number, precision: int = 2) -> str:
    return '{:0.0{}f}'.format(number, precision)


async def market_sell(buy_order):
    global PRECISIONS
    client = get_binance_client()
    executed_qty = Decimal(buy_order.get('executedQty')) * Decimal(0.99)
    quantity = format_number(number=executed_qty,
                             precision=PRECISIONS.get(PAIR))
    sell_order = client.order_market_sell(symbol=PAIR,
                                          quantity=quantity)
    return sell_order


async def send_sell_order(sell_order: dict):
    httpx.post(url=SELL_NOTIFICATION_ENDPOINT,
               json=sell_order)


async def process_message(message: aio_pika.IncomingMessage):
    async with message.process(ignore_processed=True):
        message_body = ujson.loads(message.body)
        await message.ack()

        if not message_body.get('orderId') or not message_body.get('fills'):
            return

        buy_price = Decimal(message_body.get('fills')[0].get('price'))
        stop_price = buy_price - Decimal(STOP_DELTA)
        tp_price = buy_price + Decimal(TP_DELTA)

        await monitor_price(stop_price=stop_price,
                            tp_price=tp_price)

        sell_order = await market_sell(buy_order=message_body)
        logger.info(f'Successfully sold with order id {sell_order.get("orderId")}')

        await send_sell_order(sell_order=sell_order)


async def consume_queue():
    logger.info(f'Consuming queue: {AMQP_QUEUE}')
    conn: aio_pika.Connection = await aio_pika.connect(url=AMQP_CONN_STRING)

    channel = await conn.channel()
    queue = await channel.declare_queue(name=AMQP_QUEUE,
                                        auto_delete=True)
    await queue.consume(process_message)
    return conn


async def main():
    await asyncio.gather(ticker(), consume_queue())
    logger.info('Done')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
