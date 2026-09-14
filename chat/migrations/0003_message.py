# Generated for Chat Completions migration on 2026-05-06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_sessionfeedback'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=20)),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='chat.chatsession')),
            ],
            options={
                'ordering': ['created_at', 'id'],
                'indexes': [models.Index(fields=['session', 'created_at'], name='chat_messag_session_b8a0a5_idx')],
            },
        ),
    ]
