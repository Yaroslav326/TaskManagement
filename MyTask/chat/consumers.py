from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import DenyConnection
import json


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("=== Connect called ===")
        print("Scope:", self.scope.keys())
        print("User:", self.scope["user"])
        print("Channel layer:", self.channel_layer)

        if self.scope['user'].is_anonymous:
            await self.close(code=4001)
            raise DenyConnection("Authentication required")

        self.chat_room_name = self.scope['url_route']['kwargs'][
            'chatroom_name']
        self.room_group_name = f'chat_{self.chat_room_name}'

        print("Room group name:", self.room_group_name)

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        from django.conf import settings
        print("CHANNEL_LAYERS (from settings):", settings.CHANNEL_LAYERS)
        print("Channel layer backend:", self.channel_layer)

    async def disconnect(self, close_code):
        if self.channel_layer is not None:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        else:
            print("Warning: channel_layer is None")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()
        except json.JSONDecodeError:
            return

        if not message:
            return

        username = self.scope['user'].username

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'username': username,
                'message': message
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'username': event['username'],
            'message': event['message']
        }))
