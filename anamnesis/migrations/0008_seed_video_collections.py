# Seed the two built-in video collections: structure/symptom and "10 errores".
# Idempotent — re-running the migrations on an instance that already has these
# slugs is a no-op (update_or_create on slug).

from django.db import migrations


VIDEOS_COLLECTION = {
    'slug': 'videos',
    'name': 'Anamnesis y Exploración Física en vídeo',
    'blurb': '11 vídeos docentes del Grado en Medicina de la UVa donde estudiantes demuestran cómo estructurar la anamnesis y explorar al paciente.',
    'thumb_video_id': '4bRbyfd5Fb0',
    'hero_title': 'Anamnesis y Exploración Física en vídeo',
    'hero_title_emphasis': 'Exploración Física',
    'hero_subtitle': 'Colección de 11 vídeos del Grado en Medicina de la UVa en los que estudiantes demuestran cómo estructurar la historia clínica y explorar al paciente.',
    'hero_stat_count': '11 vídeos',
    'hero_stat_count_caption': 'Colección completa',
    'hero_stat_origin': 'UVa Online',
    'hero_stat_origin_caption': 'Dir. Luis Corral Gudino',
    'intro_video_id': '4bRbyfd5Fb0',
    'intro_eyebrow': 'Vídeo introductorio',
    'intro_title': 'Anamnesis y Exploración Física — Presentación de los vídeos',
    'intro_description': 'Punto de partida de la colección docente. Presentación de los objetivos, la metodología y la estructura de los vídeos de habilidades clínicas para estudiantes de Medicina de la UVa.',
    'intro_badge_number': '01',
    'notice': 'Los vídeos se abren directamente en YouTube en el vídeo correspondiente — pulsa cualquier tarjeta para verlo.',
    'accent_color': '#003973',
    'order': 0,
    'sections': [
        {
            'title': 'Estructura de la historia clínica',
            'pip_color': '#003973',
            'order': 0,
            'videos': [
                ('r03eQUOjILE', '02', 'Estructura de la anamnesis',
                 'Cómo organizar y sistematizar la recogida de información en la historia clínica.'),
                ('2TwNvy6I_jY', '08', 'Anamnesis por aparatos',
                 'Revisión sistemática por sistemas: cómo preguntar por síntomas de cada aparato de forma ordenada.'),
                ('7B0XQdxJG_4', '09', 'Recoger los antecedentes patológicos',
                 'Cómo obtener de forma sistemática los antecedentes médicos, quirúrgicos, familiares y personales.'),
                ('yH3SSesT6p8', '10', 'Recoger los tratamientos farmacológicos',
                 'Técnica para registrar correctamente la medicación habitual, alergias e interacciones relevantes.'),
                ('bdsWaM4iP6Y', '11', 'Situación basal y grado de dependencia',
                 'Cómo valorar la funcionalidad previa del paciente: escalas de dependencia y calidad de vida basal.'),
            ],
        },
        {
            'title': 'El síntoma guía — casos prácticos',
            'pip_color': '#c60046',
            'order': 1,
            'videos': [
                ('SwyPMunC5SM', '03', 'Anamnesis del síntoma guía',
                 'Cómo identificar y explorar el síntoma principal que centra y orienta el diagnóstico diferencial.'),
                ('beGjj6WYfZo', '04', 'Anamnesis del dolor torácico',
                 'Cómo interrogar el dolor torácico para diferenciar causas cardiacas, pulmonares y benignas.'),
                ('2Cf0pw9t8YE', '05', 'Anamnesis del dolor abdominal',
                 'Claves para orientar el dolor abdominal: localización, irradiación, tipo y síntomas asociados.'),
                ('nAJvCYQqNYY', '06', 'Anamnesis de la cefalea',
                 'Cómo distinguir migraña, cefalea tensional, en racimos o señales de alarma neurológica.'),
                ('m86VOPKExwo', '07', 'Anamnesis de la disnea',
                 'Cómo evaluar la falta de aire: escalas funcionales, ortopnea, DPN y diagnóstico diferencial.'),
            ],
        },
    ],
}


ERRORES_COLLECTION = {
    'slug': 'errores',
    'name': 'Ponerse en la piel del paciente',
    'blurb': '10 vídeos breves (menos de 1 minuto cada uno) sobre los errores más frecuentes en las primeras anamnesis durante las prácticas, vistos desde el paciente.',
    'thumb_video_id': 'Ybf34xEtXJg',
    'hero_title': 'Ponerse en la piel del paciente',
    'hero_title_emphasis': 'piel del paciente',
    'hero_subtitle': '10 errores frecuentes en las primeras anamnesis durante las prácticas, vistos desde el otro lado de la consulta. Todos los vídeos duran menos de 1 minuto.',
    'hero_stat_count': '11 vídeos',
    'hero_stat_count_caption': 'Menos de 1 minuto cada uno',
    'hero_stat_origin': 'UVa Online',
    'hero_stat_origin_caption': 'Dir. Luis Corral Gudino',
    'intro_video_id': 'Ybf34xEtXJg',
    'intro_eyebrow': 'Vídeo de presentación',
    'intro_title': 'Errores comunes en la primera anamnesis',
    'intro_description': 'Introducción a la colección «Ponerse en la piel del paciente». Vídeos de menos de un minuto en los que estudiantes de Medicina reproducen los errores más frecuentes al realizar sus primeras entrevistas clínicas, vistos desde la perspectiva del paciente.',
    'intro_badge_number': '00',
    'notice': 'Los vídeos se abren directamente en YouTube en el vídeo correspondiente — pulsa cualquier tarjeta para verlo.',
    'accent_color': '#c60046',
    'order': 1,
    'sections': [
        {
            'title': 'Los 10 errores más frecuentes',
            'pip_color': '#c60046',
            'order': 0,
            'videos': [
                ('yJwk8CNaArE', '1', 'No presentarse',
                 'El paciente no sabe quién tiene delante. La presentación establece la relación de confianza que hace posible una buena entrevista.',
                 'Error 01', '<1 min'),
                ('KaSz3XNORGE', '2', 'No informar al paciente de lo que vamos a hacer',
                 'El paciente se siente interrogado sin saber por qué. Explicar el objetivo de la entrevista reduce la ansiedad y mejora la calidad de la información.',
                 'Error 02', '<1 min'),
                ('UBYKZty7phU', '3', 'Abusar de términos médicos y jerga',
                 'El paciente no entiende y asiente por no parecer ignorante. La comunicación eficaz exige adaptarse al nivel del interlocutor.',
                 'Error 03', '<1 min'),
                ('9P3C_qgD8nU', '4', 'Hacer preguntas que obligan a una respuesta concreta',
                 'Las preguntas cerradas o dirigidas sesgan la información. El paciente responde lo que cree que el médico quiere oír, no lo que realmente siente.',
                 'Error 04', '<1 min'),
                ('ehd6UBTAO8E', '5', 'No ir pregunta a pregunta',
                 'Lanzar varias preguntas a la vez desorienta al paciente, que no sabe cuál contestar primero y acaba respondiendo solo a la última.',
                 'Error 05', '<1 min'),
                ('3WrxvSY-e8I', '6', 'Perder la paciencia',
                 'El paciente habla lento, se desvía o repite. La impaciencia visible rompe la alianza terapéutica y cierra al paciente emocionalmente.',
                 'Error 06', '<1 min'),
                ('zaw7Mj0UfKc', '7', 'No mirar al paciente',
                 'Mirar solo al papel o al ordenador transmite desinterés. El contacto visual es la base de la comunicación no verbal en la relación médico-paciente.',
                 'Error 07', '<1 min'),
                ('UpVVLKJ0170', '8', 'No ser capaz de dirigir la entrevista',
                 'El paciente toma el control y la entrevista se convierte en una charla sin estructura. El médico debe guiar sin interrumpir bruscamente.',
                 'Error 08', '<1 min'),
                ('NyecsuHf7Qk', '9', 'Desordenar la anamnesis',
                 'Saltar de un bloque a otro sin orden confunde al paciente y genera lagunas de información. La estructura es la columna vertebral de la historia clínica.',
                 'Error 09', '<1 min'),
                ('jsDeS1UST2Y', '10', 'Evitar las «preguntas incómodas»',
                 'Saltarse preguntas sobre hábitos, sexualidad o salud mental por pudor deja puntos ciegos clínicos. El paciente espera ser preguntado con naturalidad y respeto.',
                 'Error 10', '<1 min'),
            ],
        },
    ],
}


def _seed_collection(VideoCollection, VideoSection, Video, payload):
    sections = payload.pop('sections')
    coll, _ = VideoCollection.objects.update_or_create(
        slug=payload['slug'], defaults=payload,
    )
    # Wipe + recreate children so re-runs match the seeded shape exactly.
    coll.sections.all().delete()
    for sec_data in sections:
        videos = sec_data.pop('videos')
        section = VideoSection.objects.create(collection=coll, **sec_data)
        for v in videos:
            youtube_id, badge, title, desc = v[:4]
            chip = v[4] if len(v) > 4 else ''
            duration = v[5] if len(v) > 5 else ''
            Video.objects.create(
                section=section,
                youtube_id=youtube_id,
                title=title,
                description=desc,
                badge_number=badge,
                chip_label=chip,
                duration_label=duration,
                order=section.videos.count(),
            )


def seed_video_collections(apps, schema_editor):
    VideoCollection = apps.get_model('anamnesis', 'VideoCollection')
    VideoSection = apps.get_model('anamnesis', 'VideoSection')
    Video = apps.get_model('anamnesis', 'Video')
    _seed_collection(VideoCollection, VideoSection, Video, dict(VIDEOS_COLLECTION))
    _seed_collection(VideoCollection, VideoSection, Video, dict(ERRORES_COLLECTION))


def remove_video_collections(apps, schema_editor):
    VideoCollection = apps.get_model('anamnesis', 'VideoCollection')
    VideoCollection.objects.filter(slug__in=['videos', 'errores']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('anamnesis', '0007_videocollection_videosection_video'),
    ]

    operations = [
        migrations.RunPython(seed_video_collections, remove_video_collections),
    ]
