from django.urls import path
from .views import home, profile, RegisterView, read, stat, my_view

urlpatterns = [
    path("", home, name="users-home"),
    path("register/", RegisterView.as_view(), name="users-register"),
    path("profile/", profile, name="users-profile"),
    path("read/", read, name="read"),
    path("stat/", stat, name="stat"),
    path("test/", my_view, name="my_view"),
]
