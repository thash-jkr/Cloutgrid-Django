from rest_framework import serializers

from .models import Conversation, Message
from users.serializers import CreatorUserSerializer, BusinessUserSerializer


class ConversationSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "user", "created_at"]

    def check_attr(self, user):
        if hasattr(user, "creatoruser"):
            return CreatorUserSerializer(user.creatoruser, context=self.context).data
        else:
            return BusinessUserSerializer(user.businessuser, context=self.context).data

    def get_user(self, obj):
        user = self.context.get("user")

        if user.id == obj.user_1.id:
            return self.check_attr(obj.user_2)
        else:
            return self.check_attr(obj.user_1)


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "sender", "content", "is_read", "created_at"]
