from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import CursorPagination
from django.shortcuts import get_object_or_404
from better_profanity import profanity
from django.db.models import Q
from django.contrib.auth import get_user_model

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()


class MessagePagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"


class ConversationListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user

        conversations = (
            Conversation.objects.filter(Q(user_1=user) | Q(user_2=user))
            .select_related("user_1", "user_2")
            .order_by("-updated_at")
        )
        serializer = ConversationSerializer(
            conversations, many=True, context={"user": user, "request": request}
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class ConversationDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_clean_user_id(self, user_1_id, user_2_id):
        if str(user_1_id) > str(user_2_id):
            return user_2_id, user_1_id
        else:
            return user_1_id, user_2_id

    def get(self, request, receiver_id):
        user = request.user

        get_object_or_404(User, id=receiver_id)

        user_1_id, user_2_id = self.get_clean_user_id(user.id, receiver_id)

        conversation = get_object_or_404(
            Conversation.objects.select_related("user_1", "user_2"),
            user_1_id=user_1_id,
            user_2_id=user_2_id,
        )
        serializer = ConversationSerializer(
            conversation, context={"user": user, "request": request}
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, receiver_id):
        user = request.user

        get_object_or_404(User, id=receiver_id)

        user_1_id, user_2_id = self.get_clean_user_id(user.id, receiver_id)

        conversation, created = Conversation.objects.get_or_create(
            user_1_id=user_1_id,
            user_2_id=user_2_id,
        )
        serializer = ConversationSerializer(conversation, context={"user": user})

        if not created:
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, conversation_id):
        user = request.user

        conversation = get_object_or_404(
            Conversation,
            Q(id=conversation_id) & Q(user_1=user) | Q(user_2=user),
        )

        paginator = MessagePagination()
        paginated_messages = paginator.paginate_queryset(
            Message.objects.filter(conversation=conversation).order_by("-created_at"),
            request,
        )

        serializer = MessageSerializer(paginated_messages, many=True)

        return paginator.get_paginated_response(serializer.data)


class MessageDetailView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, conversation_id):
        user = request.user

        content = request.data.get("content")
        if not content or content.strip() == "":
            return Response(
                {"message": "Message content cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation = get_object_or_404(
            Conversation,
            Q(id=conversation_id) & Q(user_1=user) | Q(user_2=user),
        )

        new_message = Message.objects.create(
            sender=user,
            conversation=conversation,
            content=content,
        )
        serializer = MessageSerializer(new_message)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
