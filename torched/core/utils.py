# core/utils.py

import openai
from django.conf import settings

# Ustawienie klucza API z ustawień Django
# openai.api_key = settings.OPENAI_API_KEY


def generate_flashcards(context, prompt="Generate flashcards based on the following context:"):
    """
    Generuje fiszki na podstawie dostarczonego kontekstu.

    :param context: Tekst kontekstu do generowania fiszek.
    :param prompt: Polecenie do modelu AI.
    :return: Tekst wygenerowanych fiszek.
    """
    # try:
    #     response = openai.Completion.create(
    #         engine="text-davinci-003",  # Możesz użyć nowszego modelu, jeśli jest dostępny
    #         prompt=f"{prompt}\n\n{context}",
    #         max_tokens=150,
    #         n=1,
    #         stop=None,
    #         temperature=0.7,
    #     )
    #     flashcards = response.choices[0].text.strip()
    #     return flashcards
    # except Exception as e:
    #     print(f"Error generating flashcards: {e}")
    #     return ""
    pass


def generate_exam(context, prompt="Generate an exam based on the following context:"):
    """
    Generuje egzamin na podstawie dostarczonego kontekstu.

    :param context: Tekst kontekstu do generowania egzaminu.
    :param prompt: Polecenie do modelu AI.
    :return: Tekst wygenerowanego egzaminu.
    """
    # try:
    #     response = openai.Completion.create(
    #         engine="text-davinci-003",
    #         prompt=f"{prompt}\n\n{context}",
    #         max_tokens=300,
    #         n=1,
    #         stop=None,
    #         temperature=0.7,
    #     )
    #     exam = response.choices[0].text.strip()
    #     return exam
    # except Exception as e:
    #     print(f"Error generating exam: {e}")
    #     return ""
    pass


