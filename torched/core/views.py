from rest_framework import generics, permissions, viewsets
from django.contrib.auth import get_user_model
from .models import Class, Note, Flashcard, Exam, Subject
from .serializers import (
    UserSerializer,
    ClassSerializer,
    NoteSerializer,
    FlashcardSerializer,
    ExamSerializer,
    SubjectSerializer
)
from .permissions import IsOwner
from rest_framework.decorators import action
from rest_framework.response import Response
from .documents import NoteDocument
from .utils import generate_flashcards, generate_exam
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from .documents import NoteDocument
from .serializers import NoteDocumentSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from .utils import generate_flashcards

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer

class ClassViewSet(viewsets.ModelViewSet):
    queryset = Class.objects.all()
    serializer_class = ClassSerializer
    permission_classes = [IsAuthenticated, IsOwner]

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Jeśli jesteś nauczycielem, widzisz wszystkie notatki swojej klasy
        if user.is_staff:
            return Note.objects.filter(class_assigned__teacher=user)
        # Jeśli jesteś uczniem, widzisz notatki przypisane do Twojej klasy
        return Note.objects.filter(class_assigned__students=user)

    @action(detail=True, methods=['post'])
    def generate_flashcards(self, request, pk=None):
        note = self.get_object()
        generate_flashcards(note)
        return Response({'status': 'flashcards generated'})


class FlashcardViewSet(viewsets.ModelViewSet):
    queryset = Flashcard.objects.all()
    serializer_class = FlashcardSerializer
    permission_classes = [permissions.IsAuthenticated]

class ExamViewSet(viewsets.ModelViewSet):
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def generate_exam(self, request, pk=None):
        exam = self.get_object()
        # Logika generowania egzaminu
        # TODO: Integracja z RAG do generowania pytań
        return Response({'status': 'exam generated'})


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer
    permission_classes = [IsAuthenticated]


class NoteSearchView(DocumentViewSet):
    document = NoteDocument
    serializer_class = NoteDocumentSerializer
    lookup_field = 'id'
    filter_backends = [
        # Add appropriate filter backends
    ]