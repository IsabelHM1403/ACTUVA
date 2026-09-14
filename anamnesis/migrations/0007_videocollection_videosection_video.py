# Generated for the video-collections feature on 2026-05-13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anamnesis', '0006_quizattempt_anamnesis_q_student_dfc2f2_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='VideoCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(help_text='URL part: /anamnesis/coleccion/<slug>/', unique=True)),
                ('name', models.CharField(help_text='Short label used in dashboard cards.', max_length=120)),
                ('blurb', models.CharField(help_text='Short description for the dashboard card.', max_length=300)),
                ('thumb_video_id', models.CharField(blank=True, help_text='YouTube ID used for the dashboard card thumbnail.', max_length=20)),
                ('hero_title', models.CharField(max_length=200)),
                ('hero_title_emphasis', models.CharField(blank=True, help_text='Optional italic/colored fragment of the hero title.', max_length=120)),
                ('hero_subtitle', models.TextField(blank=True)),
                ('hero_stat_count', models.CharField(blank=True, help_text='e.g. "11 vídeos"', max_length=40)),
                ('hero_stat_count_caption', models.CharField(blank=True, max_length=80)),
                ('hero_stat_origin', models.CharField(blank=True, default='UVa Online', max_length=40)),
                ('hero_stat_origin_caption', models.CharField(blank=True, default='Dir. Luis Corral Gudino', max_length=120)),
                ('intro_video_id', models.CharField(blank=True, max_length=20)),
                ('intro_eyebrow', models.CharField(blank=True, max_length=80)),
                ('intro_title', models.CharField(blank=True, max_length=200)),
                ('intro_description', models.TextField(blank=True)),
                ('intro_badge_number', models.CharField(blank=True, default='00', max_length=8)),
                ('notice', models.CharField(blank=True, help_text='Optional yellow notice line shown under the hero.', max_length=400)),
                ('accent_color', models.CharField(default='#003973', help_text='Brand color used for section pips and play-buttons.', max_length=8)),
                ('order', models.PositiveSmallIntegerField(default=0)),
            ],
            options={'ordering': ['order', 'name']},
        ),
        migrations.CreateModel(
            name='VideoSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('pip_color', models.CharField(default='#003973', help_text='Color of the small pip next to the section title.', max_length=8)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='anamnesis.videocollection')),
            ],
            options={'ordering': ['collection', 'order']},
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('youtube_id', models.CharField(help_text='The "v=" parameter from the YouTube URL.', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('badge_number', models.CharField(blank=True, help_text='Small overlay on the thumbnail, e.g. "01" / "Error 03".', max_length=10)),
                ('duration_label', models.CharField(blank=True, help_text='Optional duration hint shown above the title (e.g. "<1 min").', max_length=20)),
                ('chip_label', models.CharField(blank=True, help_text='Optional red chip above the title (e.g. "Error 01").', max_length=30)),
                ('order', models.PositiveSmallIntegerField(default=0)),
                ('section', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='videos', to='anamnesis.videosection')),
            ],
            options={'ordering': ['section', 'order']},
        ),
    ]
