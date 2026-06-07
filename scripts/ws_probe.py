import asyncio
import websockets
import json

async def run():
    uri = 'ws://ws_proxy:8787/ws/c9fff588'
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({'type':'order','order_id':42,'side':'buy','price':100,'qty':1}))
            resp = await asyncio.wait_for(ws.recv(), timeout=5)
            print('RESPONSE:', resp)
    except Exception as e:
        print('ERROR:', e)

if __name__ == '__main__':
    asyncio.run(run())
