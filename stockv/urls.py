from django.urls import path
from .views import HomeView, LoginForm, DashboardView, RegisterView, CustomLoginView, CustomLogoutView, CompanyRegistrationView, ProductCreateView, ProviderCreateView, ProductRestockView, ProductCSVImportView, ProductCSVSampleView, SaleCreateView, SaleListView, SaleDetailView, SaleConfirmView, SaleCancelView, ProfileView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('company/register/', CompanyRegistrationView.as_view(), name='company_register'),
    path('products/add/', ProductCreateView.as_view(), name='product_add'),
    path('providers/add/', ProviderCreateView.as_view(), name='provider_add'),
    path('products/<int:pk>/restock/', ProductRestockView.as_view(), name='product_restock'),
    path('products/import/', ProductCSVImportView.as_view(), name='product_csv_import'),
    path('products/import/sample/', ProductCSVSampleView.as_view(), name='product_csv_sample'),
    path('sales/add/', SaleCreateView.as_view(), name='sale_add'),
    path('sales/', SaleListView.as_view(), name='sale_list'),
    path('sales/<int:pk>/', SaleDetailView.as_view(), name='sale_detail'),
    path('sales/<int:pk>/confirm/', SaleConfirmView.as_view(), name='sale_confirm'),
    path('sales/<int:pk>/cancel/', SaleCancelView.as_view(), name='sale_cancel'),
    path('profile/', ProfileView.as_view(), name='profile'),
]

