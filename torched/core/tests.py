# core/tests.py

from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Subject, Class, Note, Flashcard, Exam
from django_elasticsearch_dsl.registries import registry
from .documents import NoteDocument

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_owner=True
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(self.user.is_owner)
        self.assertTrue(self.user.check_password('testpass123'))

    def test_user_str(self):
        self.assertEqual(str(self.user), 'testuser')


class SubjectModelTest(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name='Mathematics')

    def test_subject_creation(self):
        self.assertEqual(self.subject.name, 'Mathematics')

    def test_subject_str(self):
        self.assertEqual(str(self.subject), 'Mathematics')


class ClassModelTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='owneruser',
            password='ownerpass123',
            is_owner=True
        )
        self.student1 = User.objects.create_user(
            username='student1',
            password='studentpass123'
        )
        self.student2 = User.objects.create_user(
            username='student2',
            password='studentpass123'
        )
        self.class_instance = Class.objects.create(
            name='Class 101',
            owner=self.owner
        )
        self.class_instance.students.set([self.student1, self.student2])

    def test_class_creation(self):
        self.assertEqual(self.class_instance.name, 'Class 101')
        self.assertEqual(self.class_instance.owner, self.owner)
        self.assertIn(self.student1, self.class_instance.students.all())
        self.assertIn(self.student2, self.class_instance.students.all())

    def test_class_str(self):
        self.assertEqual(str(self.class_instance), 'Class 101')


class NoteModelTest(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name='Physics')
        self.owner = User.objects.create_user(
            username='owneruser',
            password='ownerpass123',
            is_owner=True
        )
        self.class_instance = Class.objects.create(
            name='Physics 101',
            owner=self.owner
        )
        self.note = Note.objects.create(
            title='Newton\'s Laws',
            content='Content about Newton\'s Laws',
            subject=self.subject,
            class_assigned=self.class_instance
        )

    def test_note_creation(self):
        self.assertEqual(self.note.title, 'Newton\'s Laws')
        self.assertEqual(self.note.content, 'Content about Newton\'s Laws')
        self.assertEqual(self.note.subject, self.subject)
        self.assertEqual(self.note.class_assigned, self.class_instance)

    def test_note_str(self):
        self.assertEqual(str(self.note), 'Newton\'s Laws')


class FlashcardModelTest(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name='Chemistry')
        self.owner = User.objects.create_user(
            username='owneruser',
            password='ownerpass123',
            is_owner=True
        )
        self.class_instance = Class.objects.create(
            name='Chemistry 101',
            owner=self.owner
        )
        self.note = Note.objects.create(
            title='Periodic Table',
            content='Content about the Periodic Table',
            subject=self.subject,
            class_assigned=self.class_instance
        )
        self.flashcard = Flashcard.objects.create(
            question='What is the atomic number of Hydrogen?',
            answer='1',
            note=self.note
        )

    def test_flashcard_creation(self):
        self.assertEqual(self.flashcard.question, 'What is the atomic number of Hydrogen?')
        self.assertEqual(self.flashcard.answer, '1')
        self.assertEqual(self.flashcard.note, self.note)

    def test_flashcard_str(self):
        self.assertEqual(str(self.flashcard), 'What is the atomic number of Hydrogen?')


class ExamModelTest(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name='Biology')
        self.owner = User.objects.create_user(
            username='owneruser',
            password='ownerpass123',
            is_owner=True
        )
        self.class_instance = Class.objects.create(
            name='Biology 101',
            owner=self.owner
        )
        self.exam = Exam.objects.create(
            title='Midterm Exam',
            class_assigned=self.class_instance,
            questions='Question 1: ...\nQuestion 2: ...'
        )

    def test_exam_creation(self):
        self.assertEqual(self.exam.title, 'Midterm Exam')
        self.assertEqual(self.exam.class_assigned, self.class_instance)
        self.assertIn('Question 1:', self.exam.questions)

    def test_exam_str(self):
        self.assertEqual(str(self.exam), 'Midterm Exam')


class ElasticsearchIndexTest(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name='Computer Science')
        self.owner = User.objects.create_user(
            username='owneruser',
            password='ownerpass123',
            is_owner=True
        )
        self.class_instance = Class.objects.create(
            name='CS101',
            owner=self.owner
        )
        self.note = Note.objects.create(
            title='Algorithms',
            content='Content about algorithms',
            subject=self.subject,
            class_assigned=self.class_instance
        )

    def test_elasticsearch_indexing(self):
        # Update the document in Elasticsearch
        NoteDocument().update(self.note)

        # Fetch the document from Elasticsearch registry
        documents = registry.get_documents(['core.Note'])
        # Convert the set to a list or iterate directly
        for document in documents:
            es = document.search()  # Perform search using the document instance
            response = es.query("match", title="Algorithms").execute()

            # Check if the document was properly indexed
            self.assertEqual(response.hits.total.value, 1)
            self.assertEqual(response.hits[0].title, 'Algorithms')

    def tearDown(self):
        # Optionally, delete the indexed document after the tests
        self.note.delete()  # Delete the note instance from the database
