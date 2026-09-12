from django.urls import path
from .views import HomeView, LoginForm, DashboardView, RegisterView, CustomLoginView, CustomLogoutView, CompanyRegistrationView, ProductCreateView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('company/register/', CompanyRegistrationView.as_view(), name='company_register'),
    path('products/add/', ProductCreateView.as_view(), name='product_add'),    
]

