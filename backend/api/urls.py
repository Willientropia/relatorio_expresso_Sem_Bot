# backend/api/urls.py
from django.urls import path
from . import views
from .views import RegisterView, ConfirmEmailView, LoginView

urlpatterns = [
    # Rotas de Autenticação
    path('register/', RegisterView.as_view(), name='register'),
    path('confirm-email/<str:uidb64>/<str:token>/', ConfirmEmailView.as_view(), name='confirm-email'),
    path('login/', LoginView.as_view(), name='login'),

    # Rotas existentes
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:customer_id>/ucs/', views.uc_list, name='uc_list'),
    path('customers/<int:customer_id>/ucs/<int:uc_id>/', views.uc_detail, name='uc_detail'),
    path('customers/<int:customer_id>/ucs/<int:uc_id>/toggle/', views.uc_toggle_status, name='uc_toggle_status'),
    
    # Novas rotas para faturas
    path('customers/<int:customer_id>/faturas/tasks/', views.get_fatura_tasks, name='get_fatura_tasks'),
    path('customers/<int:customer_id>/faturas/', views.get_faturas, name='get_faturas'),
    path('customers/<int:customer_id>/faturas/import/', views.start_fatura_import, name='start_fatura_import'),
]