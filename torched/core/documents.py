# core/documents.py

from django_elasticsearch_dsl import Document, Index, fields
from .models import Note, Subject
from django.contrib.auth import get_user_model

User = get_user_model()

# Definiowanie indeksu Elasticsearch
notes_index = Index('notes')

# Konfiguracja ustawień indeksu
notes_index.settings(
    number_of_shards=1,
    number_of_replicas=0
)

@notes_index.doc_type
class NoteDocument(Document):
    subject = fields.ObjectField(properties={
        'name': fields.TextField(),
    })
    class_assigned = fields.ObjectField(properties={
        'name': fields.TextField(),
        'owner': fields.ObjectField(properties={
            'username': fields.TextField(),
        }),
    })

    class Django:
        model = Note  # Model powiązany z tym dokumentem

        # Pola modelu, które mają być indeksowane w Elasticsearch
        fields = [
            'title',
            'content',
            'created_at',
            'updated_at',
        ]
