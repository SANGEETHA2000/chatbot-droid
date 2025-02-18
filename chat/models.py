import uuid
from django.db import models
from django.utils import timezone

class Conversation(models.Model):
    channel_id = models.CharField(max_length=100)
    thread_ts = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['channel_id', 'thread_ts']),
        ]

def generate_message_id():
    """
    Generates a unique message ID using UUID.
    """
    return f"msg_{uuid.uuid4().hex}"

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    is_bot = models.BooleanField(default=False)
    user_id = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    message_id = models.CharField(max_length=100, unique=True,default=generate_message_id)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp']),
        ]