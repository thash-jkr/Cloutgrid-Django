import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_1")
    user_2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conversation_2")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user_1", "user_2"], name="unique_conversation_pair")
        ]
        
    def clean(self):
        if self.user_1 == self.user_2:
            raise ValidationError("You cannot start a conversation with yourself")
        
    def save(self, *args, **kwargs):
        if self.user_1_id and self.user_2_id and self.user_1_id > self.user_2_id:
            self.user_1, self.user_2 = self.user_2, self.user_1
            
        self.full_clean()
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"Chat: {self.user_1.username} & {self.user_2.username}"


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ["created_at"]
        
    def __str__(self):
        return f"From {self.sender.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
