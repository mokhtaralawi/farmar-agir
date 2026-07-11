from django.urls import path
from . import views
from . import webauthn_views

app_name = 'accounts'

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('users/', views.users_list, name='users_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/toggle/', views.user_toggle_active, name='user_toggle_active'),
    # WebAuthn
    path('webauthn/begin-register/', webauthn_views.begin_registration, name='webauthn_begin_register'),
    path('webauthn/finish-register/', webauthn_views.finish_registration, name='webauthn_finish_register'),
    path('webauthn/begin-login/', webauthn_views.begin_login, name='webauthn_begin_login'),
    path('webauthn/finish-login/', webauthn_views.finish_login, name='webauthn_finish_login'),
    path('webauthn/disable/', webauthn_views.disable_webauthn, name='webauthn_disable'),
    path('webauthn/status/', webauthn_views.status, name='webauthn_status'),
]
