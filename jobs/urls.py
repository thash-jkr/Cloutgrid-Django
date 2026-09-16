from django.urls import path
from .views import (JobListView, JobDetailView, 
                    ApplyJobView)

urlpatterns = [
    path('', JobListView.as_view(), name='job-list'),
    path('<int:pk>/', JobDetailView.as_view(), name='job-detail'),
    path('<int:pk>/apply/', ApplyJobView.as_view(), name='apply-job'),
]
