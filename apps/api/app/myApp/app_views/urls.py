from django.urls import path, include
from .views import CreateAPIView, RUDView, ReadAPIView

urlpatterns=[
    path("create_session/",CreateAPIView.as_view(),name="create-session"),
    path("manage_session/<int:pk>/",RUDView.as_view(),name="manage-sessions"),
    path("sessions/",ReadAPIView.as_view(),name="read-sessions"),
]