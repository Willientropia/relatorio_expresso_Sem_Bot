# backend/api/urls.py - Adicionar estas rotas

from django.urls import path
from . import views
from .views import RegisterView, ConfirmEmailView, LoginView

# backend/api/urls.py - ADICIONAR esta linha na lista de urlpatterns

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
    
    # Rotas de faturas melhoradas
    path('customers/<int:customer_id>/faturas/', views.get_faturas, name='get_faturas'),
    path('customers/<int:customer_id>/faturas/por-ano/', views.get_faturas_por_ano, name='get_faturas_por_ano'),
    path('customers/<int:customer_id>/faturas/import/', views.start_fatura_import, name='start_fatura_import'),
    path('customers/<int:customer_id>/faturas/tasks/', views.get_fatura_tasks, name='get_fatura_tasks'),
    path('faturas/<int:fatura_id>/logs/', views.get_fatura_logs, name='get_fatura_logs'),
    
    # Upload de faturas
    path('customers/<int:customer_id>/faturas/upload/', views.upload_faturas, name='upload_faturas'),
    path('customers/<int:customer_id>/faturas/upload-with-extraction/', 
         views.upload_faturas_with_extraction, name='upload_faturas_with_extraction'),
    
    # ✅ ADICIONAR: Rota para force upload
    path('customers/<int:customer_id>/faturas/force-upload/', 
         views.force_upload_fatura, name='force_upload_fatura'),
    
    # Extração de dados de fatura
    path('extract-fatura-data/', views.extract_fatura_data, name='extract_fatura_data'),
    path('faturas/extract_data/', views.extract_fatura_data_view, name='extract_fatura_data_view'),
]