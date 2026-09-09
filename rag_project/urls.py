"""
Django URL configuration.
Django 仅负责 Admin 后台管理。
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
]
