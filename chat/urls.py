from django.urls import path
from . import views

urlpatterns = [
    path('iniciar/<slug:assistant_slug>/', views.start_session, name='start_session'),
    path('sesion/<int:session_id>/', views.chat_session_view, name='chat_session'),
    path('sesion/<int:session_id>/enviar/', views.send_message, name='send_message'),
    path('sesion/<int:session_id>/terminar/', views.end_session, name='end_session'),
    path('sesion/<int:session_id>/evaluacion/', views.session_feedback_view, name='session_feedback'),
]
