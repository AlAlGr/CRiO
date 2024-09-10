"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from telegram_miniapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.auth_view, name='auth'),
    path('home2/', views.home2_view, name='home'),
    path('frens/', views.frens_view, name='frens'),
    path('wallet/', views.wallet_view, name='wallet'),
    path('tasks/', views.tasks_view, name='tasks'),
    path('buy-character/<int:character_id>/', views.buy_character_view, name='buy_character'),
    path('buy-improvement/<int:improvement_id>/', views.buy_improvement_view, name='buy_improvement'),
    path('save_user/', views.save_user, name='save_user'),
    path('buy/character/', views.buy_character_view, name='buy_character'),
    path('buy/booster/', views.buy_boosters_view, name='buy_booster'),
    path('collect_points/', views.collect_points_view, name='collect_points'),
]

