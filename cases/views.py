from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import ClinicalCase
from .forms import ClinicalCaseForm


def profesor_required(view_func):
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_profesor() and not request.user.is_staff:
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__
    return wrapper


@profesor_required
def case_list(request):
    cases = ClinicalCase.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'cases/list.html', {'cases': cases})


@profesor_required
def case_create(request):
    if request.method == 'POST':
        form = ClinicalCaseForm(request.POST, request.FILES)
        if form.is_valid():
            case = form.save(commit=False)
            case.created_by = request.user
            case.save()
            return redirect('case_list')
    else:
        form = ClinicalCaseForm()
    return render(request, 'cases/create.html', {'form': form})


@profesor_required
def case_toggle(request, case_id):
    case = get_object_or_404(ClinicalCase, id=case_id, created_by=request.user)
    case.is_active = not case.is_active
    case.save(update_fields=['is_active'])
    return redirect('case_list')
