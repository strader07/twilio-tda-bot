
from django.urls import path, re_path, include
from main import views
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import url

urlpatterns = [

    re_path(r'^.*\.html', views.pages, name='pages'),

    path('', views.index, name='home'),
    path('save_setting/', views.save_setting, name='save_setting'),
    path('bot/', views.get_bot_triggers, name='bot')
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)