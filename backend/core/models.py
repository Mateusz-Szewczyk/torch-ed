from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Avg

class User(AbstractUser):
    """
    """
    favourite = models.ManyToManyField('Flashcard', blank=True)

    def __str__(self) -> str:
        return self.username


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name


class Subject(models.Model):
    """
    Model przedmiotu, do którego mogą być przypisane notatki.
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name


# class Token(models.Model):
#     # user_id = models.IntegerField()
#     user_id = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='author')
#     owner = models.ForeignKey(User, on_delete=models.CASCADE, null=False, related_name='owner')
#     jti = models.CharField(max_length=36, unique=True)
#     token = models.CharField(max_length=500)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateField(auto_now_add=True)
#     expires_at = models.DateField(null=True)

#     def __str__(self) -> str:
#         return f'Token for {self.owner} - from {self.author}. {self.is_active}'
    

class Flashcard(models.Model):
    """
    Model fiszki powiązanej z konkretną notatką.
    """
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=False)
    subject = models.ForeignKey(Subject, related_name='category', on_delete=models.PROTECT, blank=True, null=True)
    # note = models.ForeignKey(Note, related_name='flashcards', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    is_correct = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.question
    

class BadAnswer(models.Model):

    answer = models.TextField()
    related_question = models.ManyToManyField(Flashcard, related_name='badAnswers')
    author = models.ForeignKey(User, on_delete=models.PROTECT)

    
class FlashcardDifficulty(models.Model):

    rating = models.IntegerField(validators=[
        MinValueValidator(1),
        MaxValueValidator(5),
    ])    
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)


class Note(models.Model):
    """
    Model notatki przypisanej do konkretnego przedmiotu i klasy.
    """
    title = models.CharField(max_length=200)
    content = models.TextField()
    subject = models.ForeignKey(Subject, related_name='notes', on_delete=models.CASCADE)
    # is there a need to class?
    # class_assigned = models.ForeignKey(Class, related_name='notes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    related_flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.title


class Exam(models.Model):
    """
    Model egzaminu przypisanego do konkretnej klasy.
    """
    title = models.CharField(max_length=200)
    # class_assigned = models.ForeignKey(Class, related_name='exams', on_delete=models.CASCADE)
    flashcards = models.ManyToManyField(Flashcard, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    privacy = models.BooleanField(default=False)

    # token = models.CharField(max_length=100, blank=True, null=True)

    @property
    def flashcard_count(self) -> int:
        return self.flashcards.count()
    
    @property
    def exam_difficulty(self) -> int:
        avg_difficulty = FlashcardDifficulty.objects.filter(flashcard__in=self.flashcards.all()).aggregate(Avg('rating'))
        return avg_difficulty['rating__avg'] or 0 

    def __str__(self) -> str:
        return self.title

class ExamRating(models.Model):

    rating = models.IntegerField(validators=[
        MinValueValidator(1),
        MaxValueValidator(5),
    ])    
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
