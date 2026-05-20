from django.urls import path
from . import views

urlpatterns = [
    path("", views.crawler_tasks, name="crawler_tasks"),
    path("create/", views.create_task, name="create_task"),
    path("<int:pk>/", views.task_detail, name="task_detail"),
]
