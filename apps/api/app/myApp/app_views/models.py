from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from django.db import models


# Create your models here.

class Chats(models.Model):
    human_query=models.TextField(max_length=1000, null=False)
    model_response=models.TextField(max_length=10000, default="Loading...", null=False)
    uploaded_file=models.FileField(
        upload_to="Cache",
        null=True,
        blank=True
    )
    time=models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'app_views'

    def __str__(self):
        return self.human_query