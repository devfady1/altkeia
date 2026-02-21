import json

try:
    from channels.generic.websocket import AsyncWebsocketConsumer

    class UpdateConsumer(AsyncWebsocketConsumer):
        async def connect(self):
            self.room_group_name = 'cafe_updates'
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()

        async def disconnect(self, close_code):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        async def receive(self, text_data):
            data = json.loads(text_data)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'update_message',
                    'message': data
                }
            )

        async def update_message(self, event):
            await self.send(text_data=json.dumps(event['message']))

except ImportError:
    # Channels not installed
    pass
