# Generated by Django 4.2.16 on 2024-10-24 16:46

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_token'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='token',
            name='author',
        ),
        migrations.AlterField(
            model_name='token',
            name='user_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='author', to=settings.AUTH_USER_MODEL),
        ),
    ]