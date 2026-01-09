from channels.generic.websocket import AsyncWebsocketConsumer
from company.models import Department, Company
from .models import Message
import json
from asgiref.sync import sync_to_async


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close(code=4001)
            return

        self.user = self.scope['user']
        self.chat_room_name = self.scope['url_route']['kwargs'][
            'chatroom_name']
        self.room_group_name = f'chat_{self.chat_room_name}'

        if self.chat_room_name == 'company':
            try:
                company = await sync_to_async(Company.objects.get)(
                    departments__personnel=self.user
                )
                self.company = company
                self.department = None
            except Company.DoesNotExist:
                await self.close(code=4003)
                return
        elif self.chat_room_name.startswith('department_'):
            try:
                dept_id_str = self.chat_room_name.split('department_', 1)[
                    1]
                dept_id = int(dept_id_str)

                department = await sync_to_async(
                    Department.objects.select_related('company').get)(
                    id=dept_id)

                if not await sync_to_async(department.personnel.filter(
                        id=self.user.id).exists)():
                    print(
                        f"User {self.user} not in department {department.name}")
                    await self.close(code=4003)
                    return

                self.department = department
                self.company = department.company

            except (ValueError, Department.DoesNotExist):
                print("Department not found or invalid ID:",
                      self.chat_room_name)
                await self.close(code=4004)
                return
        else:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        print(f"User {self.user.username} connected to {self.chat_room_name}")
        await self.send_chat_history()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name') and self.channel_layer is not None:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        else:
            print("Warning: channel_layer is None or room_group_name not set")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_text = data.get('message', '').strip()
        except json.JSONDecodeError:
            return

        if not message_text:
            return

        await self.save_message(message_text)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'username': self.user.username,
                'message': message_text
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'username': event['username'],
            'message': event['message']
        }))

    @sync_to_async
    def save_message(self, message_text):
        Message.objects.create(
            message=message_text,
            user=self.user,
            company=self.company,
            department=self.department
        )

    @sync_to_async
    def get_chat_history(self):
        messages = Message.objects.filter(
            company=self.company,
            department=self.department
        ).select_related('user').order_by('-id')[:50]
        return [
                   {
                       'username': msg.user.username,
                       'message': msg.message
                   }
                   for msg in messages
               ][::-1]

    async def send_chat_history(self):
        history = await self.get_chat_history()
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': history
        }))
