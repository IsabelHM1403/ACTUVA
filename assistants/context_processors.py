from assistants.models import Assistant

def assistant_list(request):
    return {'all_assistants': Assistant.objects.all()}
