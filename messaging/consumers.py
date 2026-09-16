import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Conversation, Message
from .serializers import MessageSerializer

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"
        self.room_joined = False

        # GATE 1: Authentication
        if not self.user.is_authenticated:
            await self.close()
            return

        # GATE 2: Conversation Membership
        is_member = await self.is_conversation_member()
        
        if not is_member:
            await self.close()
            return

        # SUCCESS
        await self.accept()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        self.room_joined = True

    async def disconnect(self, close_code):
        if getattr(self, "room_joined", False):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name,
            )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
        except json.JSONDecodeError:
            return

        content = text_data_json.get("content", "").strip()

        if not content:
            return

        serialized_payload = await self.save_message(content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "payload": serialized_payload
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    @database_sync_to_async
    def is_conversation_member(self):
        return Conversation.objects.filter(
            id=self.conversation_id
        ).filter(
            Q(user_1=self.user) | Q(user_2=self.user)
        ).exists()

    @database_sync_to_async
    def save_message(self, content):
        message = Message.objects.create(
            conversation_id=self.conversation_id,
            sender=self.user,
            content=content,
        )
        
        serializer = MessageSerializer(message)

        return serializer.data