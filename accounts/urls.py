from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import AccountDetailView, AccountListView, HistoryView, LedgerTokenObtainPairView, MeView

urlpatterns = [
    path('login/', LedgerTokenObtainPairView.as_view()),
    path('refresh/', TokenRefreshView.as_view()),
    path('me/', MeView.as_view()),
    path('accounts/', AccountListView.as_view()),
    path('accounts/<int:pk>/', AccountDetailView.as_view()),
    path('history/', HistoryView.as_view()),
]
