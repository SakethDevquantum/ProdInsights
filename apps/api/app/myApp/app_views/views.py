from django.shortcuts import render
# pyrefly: ignore [missing-import]
from .serializers import ChatSerializers
from .models import Chats
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
import subprocess
import sys
import os


class CreateAPIView(generics.CreateAPIView):
    serializer_class = ChatSerializers
    queryset = Chats.objects.all()

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        views_dir = os.path.dirname(os.path.abspath(__file__))

        project_root = os.path.normpath(os.path.join(views_dir, *(['..'] * 5)))
        model_script = os.path.join(project_root, 'models', 'agents', 'model.py')
        log_path = os.path.join(project_root, 'model_subprocess.log')

        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        with open(log_path, 'a', encoding='utf-8') as log_file:
            subprocess.Popen(
                [sys.executable, model_script],
                cwd=project_root,
                stdout=log_file,
                stderr=log_file,
                env=env,
            )

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class RUDView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ChatSerializers
    queryset = Chats.objects.all()


class ReadAPIView(generics.ListAPIView):
    serializer_class = ChatSerializers
    queryset = Chats.objects.all()