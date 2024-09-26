from rest_framework import serializers
from .models import User, Class, Subject, Note, Flashcard, Exam
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from .documents import NoteDocument


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_owner']

class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'

class ClassSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    students = UserSerializer(many=True, read_only=True)

    class Meta:
        model = Class
        fields = '__all__'

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = '__all__'

class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = '__all__'

class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = '__all__'

class NoteDocumentSerializer(DocumentSerializer):
    class Meta:
        document = NoteDocument
        fields = (
            'id',
            'title',
            'content',
            'subject',
        )