from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from assistants.models import Assistant


def _split_assistants(assistants):
    """Split assistants into clinical-skills vs. subject-revision groups.

    ReumatIA (and any future infectious / cardio / endocrino assistants tagged
    with ``phase='asignatura'``) are pedagogically different from the others:
    they help students revise a chunk of the syllabus rather than train
    anamnesis or physical exam. Surface them in their own section so the
    landing/panel doesn't lump everything together.
    """
    clinical = []
    asignatura = []
    for a in assistants:
        if a.phase == Assistant.Phase.ASIGNATURA:
            asignatura.append(a)
        else:
            clinical.append(a)
    return clinical, asignatura


def landing(request):
    if request.user.is_authenticated:
        return _dashboard(request)
    assistants = list(Assistant.objects.all())
    clinical, asignatura = _split_assistants(assistants)
    return render(request, 'landing.html', {
        'assistants': assistants,
        'assistants_clinical': clinical,
        'assistants_asignatura': asignatura,
    })


@login_required
def dashboard(request):
    return _dashboard(request)


def _dashboard(request):
    user = request.user
    if user.is_estudiante():
        assistants = [a for a in Assistant.objects.all() if a.is_available_for_curso(user.curso)]
    else:
        assistants = list(Assistant.objects.all())
    clinical, asignatura = _split_assistants(assistants)
    return render(request, 'dashboard.html', {
        'assistants': assistants,
        'assistants_clinical': clinical,
        'assistants_asignatura': asignatura,
    })
