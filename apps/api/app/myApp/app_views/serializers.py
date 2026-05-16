from rest_framework import serializers

from .models import Chats

class ChatSerializers(serializers.ModelSerializer):
    class Meta:
        model=Chats
        fields=["id", "human_query", "uploaded_file", "time", "model_response"]