from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse

from .utils import chatbot_get_answer


User = get_user_model()


def index(request: HttpRequest) -> HttpResponse:
    ...

def login(request: HttpRequest) -> HttpResponse:
    ...

def register(request: HttpRequest) -> HttpResponse:
    ...

def learn(request: HttpRequest) -> HttpResponse:
    answer = chatbot_get_answer('user123', 'Who is Amos Tversky?')
    return HttpResponse(answer)
