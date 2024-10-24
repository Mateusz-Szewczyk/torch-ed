from typing import Dict, Any, Type
from rest_framework import generics, permissions
from django.contrib.auth import get_user_model
from ...serializers import (
    UserSerializer,
)

