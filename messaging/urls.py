from django.urls import path

from messaging.views import ConversationListView, ConversationDetailView, MessageListView, MessageDetailView

urlpatterns = [
    path("", ConversationListView.as_view(), name="conversation_list"),
    path("<int:receiver_id>/", ConversationDetailView.as_view(), name="conversation_detail"),
    path("<uuid:conversation_id>/messages/", MessageListView.as_view(), name="message_list"),
    path("<uuid:conversation_id>/messages/create/", MessageDetailView.as_view(), name="message_detail"),
]