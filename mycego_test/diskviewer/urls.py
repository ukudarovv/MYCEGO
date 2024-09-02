from django.urls import path
from .views import download_file, file_list, download_selected_files

urlpatterns = [
    path('file-list/', file_list, name='file_list'),
    path('download-file/<path:file_url>/', download_file, name='download_file'),
    path('download-selected-files/', download_selected_files, name='download_selected_files'),
]
