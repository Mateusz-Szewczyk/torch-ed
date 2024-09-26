# core/admin.py

from django.contrib import admin
from .models import User, Class, Subject, Note, Flashcard, Exam
from django.contrib.auth.admin import UserAdmin

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'email', 'is_owner', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('is_owner',)}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Class)
admin.site.register(Subject)
admin.site.register(Note)
admin.site.register(Flashcard)
admin.site.register(Exam)
