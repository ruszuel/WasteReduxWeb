from django.contrib import admin
from . import views
from .views import user_list
from .views import user_activity_list
from django.urls import path, include 
from django.conf import settings
from django.conf.urls.static import static
from .views import custom_bad_request, custom_permission_denied, custom_page_not_found, custom_server_error

handler400 = 'myapp.views.custom_bad_request'
handler403 = 'myapp.views.custom_permission_denied'
handler404 = 'myapp.views.custom_page_not_found'
handler500 = 'myapp.views.custom_server_error'


urlpatterns = [
    path('', views.index, name='index'),
    path('index', views.index, name='index'), 
    path('send_verification_email/', views.send_verification_email, name='send_verification_email'),
    path('send_verification/', views.send_verification_email, name='send_verification'),
    path('verify_email/<str:token>/', views.verify_email, name='verify_email'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profiles/', views.profiles, name='profiles'),
    path('users/', views.user_list, name='users'),
    path('userinfo/<str:email_address>/', views.user_activity_list, name='user_activity_list'),
    path('filtering/', views.filtering, name='filtering'),
    path('changepass/', views.changepass, name='changepass'),
    path('verifypass/', views.verifypass, name='verifypass'),
    path('registerwaste/', views.registerwaste, name='registerwaste'),
    path('successfulreg/', views.successfulreg, name='successfulreg'),
    path('successfuladd/', views.successfuladd, name='successfuladd'),
    path('set_violation_notice/<str:user_email>/', views.set_violation_notice, name='set_violation_notice'),
    path('suspend_user/', views.suspend_user, name='suspend_user'),
    path('delete_user/', views.delete_user, name='delete_user'),
    path('update_user_status/<str:email_address>/', views.update_user_status, name='update_user_status'),
    path('dashboard/', views.college_dept_data, name='college_dept_data'),
    path('get-scanned-percentages/', views.get_scanned_percentages, name='get_scanned_percentages'),
    path('get_scanned_counts_by_college/', views.get_waste_data_by_college, name='get_scanned_counts_by_college'),
    path('get_waste_data_by_college/', views.get_waste_data_by_college, name='get_waste_data_by_college'),
    path('get_user_activity_data/', views.get_user_activity_data, name='get_user_activity_data'),
    path('filteredimages/', views.filteredimages, name='filteredimages'),
    path('update-flagged/', views.update_flagged_status, name='update_flagged_status'),
    path('update-recognized/', views.update_recognized_status, name='update_recognized_status'),
    path('add_to_dataset/', views.add_to_dataset, name='add_to_dataset'),
    path('clear-messages/', views.clear_messages, name='clear_messages'),
    path('get_table_data/', views.get_table_data, name='get_table_data'),
    path('export_filtered_college_data/', views.export_filtered_college_data, name='export_filtered_college_data'),
    path('get_summary_table_data/', views.get_summary_table_data, name='get_summary_table_data'),



    path('temp/', views.temp, name='temp'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

import logging
logger = logging.getLogger('django')
logger.debug(f"STATICFILES_DIRS: {settings.STATICFILES_DIRS}")
logger.debug(f"STATIC_ROOT: {settings.STATIC_ROOT}")
