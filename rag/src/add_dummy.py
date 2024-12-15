from rag.src.models import Exam, ExamQuestion, ExamAnswer
from rag.src.database import engine, SessionLocal

session = SessionLocal(bind=engine)

# Tworzenie egzaminu
exam = Exam(name="Egzamin z Matematyki", description="Egzamin końcowy z matematyki.")
session.add(exam)
session.commit()

# Dodawanie pytania do egzaminu
question = ExamQuestion(text="Jaka jest wartość liczby pi?", exam_id=exam.id)
session.add(question)
session.commit()

# Dodawanie odpowiedzi do pytania
answers = [
    ExamAnswer(text="3.14", is_correct=True, question_id=question.id),
    ExamAnswer(text="2.71", is_correct=False, question_id=question.id),
    ExamAnswer(text="1.62", is_correct=False, question_id=question.id),
    ExamAnswer(text="1.41", is_correct=False, question_id=question.id),
]
session.add_all(answers)
session.commit()

session.close()
