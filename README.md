# Binance Seller

The seller is selling by setting a fix delta for stop loss and take profit prices.

## Env Vars

| Name | Description |
| :--- | :--- |
| `AMQP_CONN_STRING` | Required string |
| `AMQP_QUEUE` | Required string, also known as routing key |
| `API_KEY` | Required string |
| `API_SECRET` | Required string |
| `PAIR` | Required string |
| `TP_DELTA` | Required string, in quote pips |
| `STOP_DELTA` | Required string, in quote pips |
