# core/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

class User(AbstractUser):
    """
    Niestandardowy model użytkownika rozszerzający AbstractUser.
    Dodaje pole `is_owner` do rozróżnienia właścicieli od innych użytkowników.
    """
    is_owner = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class Subject(models.Model):
    """
    Model przedmiotu, do którego mogą być przypisane notatki.
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Class(models.Model):
    """
    Model klasy, która ma przypisanego właściciela i wielu uczniów.
    """
    name = models.CharField(max_length=100)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='owned_classes', on_delete=models.CASCADE)
    students = models.ManyToManyField(User, related_name='enrolled_classes', blank=True)

    def __str__(self):
        return self.name


class Note(models.Model):
    """
    Model notatki przypisanej do konkretnego przedmiotu i klasy.
    """
    title = models.CharField(max_length=200)
    content = models.TextField()
    subject = models.ForeignKey(Subject, related_name='notes', on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, related_name='notes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Flashcard(models.Model):
    """
    Model fiszki powiązanej z konkretną notatką.
    """
    question = models.CharField(max_length=255)
    answer = models.TextField()
    note = models.ForeignKey(Note, related_name='flashcards', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question


class Exam(models.Model):
    """
    Model egzaminu przypisanego do konkretnej klasy.
    """
    title = models.CharField(max_length=200)
    class_assigned = models.ForeignKey(Class, related_name='exams', on_delete=models.CASCADE)
    questions = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

