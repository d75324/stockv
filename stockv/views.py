from .forms import UserRegistrationForm, UserLoginForm, CompanyRegistrationForm, ProductForm, ProviderForm, ProductRestockForm
from .models import Product, WarehouseTransfer, Company, User, Warehouse, Membership, WarehouseStock, UnitOfMeasure, StockMovement, Provider
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView, CreateView, FormView
from django.views.generic.edit import CreateView
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
# from django.views.generic import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

User = get_user_model()

class HomeView(TemplateView):
    # get_template_names() es un método que viene en TemplateView, lo sobre-escribimos para cambiar el template que va a usar la vista.
    def get_template_names(self):
        if self.request.user.is_authenticated:
            return ["dashboard/index.html"]
    
        return ["home.html"]
    template_name = 'home.html'


class LoginForm(TemplateView):
    template_name = "accounts/login.html"


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # definimos company
        company = Company.objects.filter(owner=user).first()
        
        # si no es dueño, buscamos por Membership
        if not company:
            membership = user.memberships.filter(is_active=True).first()
            if membership:
                company = membership.company
        # pasamos company al context
        context['company'] = company

        # pasamos también el depósito central o el depósito por defecto
        if company:
            # Buscamos el primer depósito de la empresa (o el que definiste como por defecto)
            default_warehouse = Warehouse.objects.filter(company=company).first()
            context['default_warehouse'] = default_warehouse
        else:
            context['default_warehouse'] = None

        if company:
            products = Product.objects.filter(company=company, is_active=True)
            
            # semáforos del dashboard
            context['total_stock_units'] = sum([p.current_stock for p in products])
            context['low_stock_count'] = sum([1 for p in products if p.is_below_min_stock])
            context['pending_transfers'] = WarehouseTransfer.objects.filter(
                company=company, 
                status='pending'
            ).count()
            
            # Listado rápido para la tabla inferior
            context['product_list'] = products.order_by('-created_at')[:5]
        else:
            context['total_stock_units'] = 0
            context['low_stock_count'] = 0
            context['pending_transfers'] = 0
            context['product_list'] = []

        return context


class RegisterView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('company_register')  # despues que se registre, va al formulario para crear la company

    # El método def form_valid(self, form) retorna super().form_valid(form) lo cual se usa como un punto de extensión o "hook" dejado a propósito. Se usa para interceptar el proceso justo antes o después de guardar, por ejemplo 1. iniciar sesión automáticamente tras registrarse, 2. asignar campos automáticos desde la request (ej. la compañía) o 3. enviar un email de bienvenida o notificación.
    
    def form_valid(self, form):
        # Lógica adicional: el usuario se guarda en la base de datos
        response = super().form_valid(form)
        # 2. Inicia sesión automáticamente con el usuario recién creado (self.object)
        login(self.request, self.object)
        # 3. Retorna la respuesta para que ejecute la redirección a 'company_register'
        return response


class CustomLoginView(LoginView):
    form_class = UserLoginForm
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    
    
    def form_valid(self, form):
        # Obtenemos el usuario que se está autenticando
        user = form.get_user()
        
        # Actualizamos la fecha y hora de la última actividad
        user.last_active = timezone.now()
        user.save(update_fields=['last_active'])  # Guardamos solo este campo para mayor optimización
        
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    http_method_names = ['post', 'get']


class CompanyRegistrationView(LoginRequiredMixin, CreateView):
    model = Company
    form_class = CompanyRegistrationForm
    template_name = 'accounts/company_register.html'
    success_url = reverse_lazy('dashboard')  # por ahora dashboard

    def form_valid(self, form):
        # por defecto, el usuario logueado es el dueño de la empresa
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        


        # creamos el depósito por defecto para esta empresa recién creada
        Warehouse.objects.get_or_create(
            company=self.object,
            name="Depósito Central",
            defaults={
                'code': 'CENTRAL',
                'address': self.object.address,
                'city': self.object.city,
            }
        )

        # creamos la membresía de tipo 'owner'
        Membership.objects.get_or_create(
            user=self.request.user,
            company=self.object,
            defaults={'role': 'owner', 'is_active': True}
        )
        
                # Creamos automáticamente la Unidad de Medida por defecto ("Unidades")
        UnitOfMeasure.objects.get_or_create(
            company=self.object,
            name="Unidades",
            defaults={'abbreviation': 'UN'}
        )

        return response


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    success_url = reverse_lazy('dashboard')  # ¿¿¿¿DONDE LO MANDO DESPUÉS DE CREADO!?!???
    
    def get_company(self):
        """
        Método auxiliar para no repetir la lógica de búsqueda de la compañía
        """
        user = self.request.user
        company = Company.objects.filter(owner=user).first()
        if not company:
            membership = user.memberships.filter(is_active=True).first()
            if membership:
                company = membership.company
        return company
    
    # El método get_form_kwargs en las vistas encargadas de procesar formularios (como CreateView, UpdateView o FormView) es responsable de construir y retornar el diccionario de argumentos con el que se va a instanciar el formulario.    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_company()
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # mando la compañía al contexto para poder usarla en el template
        # context['company'] = self.get_company() # La variable local no puede ser 'company' ya que se confunde con el campo del modelo. Así uqe lo vamos a llamar user_company, para evitar problemas.

        ##### ============= ERROR ============ #####
        # estoy pasando al context cosas que no necesito #
        user_company = self.get_company()
        context['company'] = user_company
        
        # paso todos los productos de la compañía
        context['product_list'] = Product.objects.filter(company=user_company).order_by('-id')
        return context

    def form_valid(self, form):
        company = self.get_company()
        form.instance.company = company
        response = super().form_valid(form)
        
        initial_stock = form.cleaned_data.get('initial_stock') or 0

        default_warehouse = Warehouse.objects.filter(company=company).first()
        if default_warehouse:
            WarehouseStock.objects.get_or_create(
                product=self.object,
                warehouse=default_warehouse,
                defaults={'quantity': initial_stock}
            )
            if initial_stock > 0:
                StockMovement.objects.create(
                    company=company,
                    product=self.object,
                    warehouse=default_warehouse,
                    movement_type='in',
                    quantity=initial_stock,
                    user=self.request.user, # quien cargó el stock? >> auditoría
                    reason='Stock inicial'
                )
                
        return response


class ProviderCreateView(LoginRequiredMixin, CreateView):
    model = Provider
    form_class = ProviderForm
    template_name = 'inventory/provider_form.html'
    success_url = reverse_lazy('dashboard')

    def get_company(self):
        user = self.request.user
        company = Company.objects.filter(owner=user).first()
        if not company:
            membership = user.memberships.filter(is_active=True).first()
            if membership:
                company = membership.company
        return company

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_company()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = self.get_company()
        return context

    def form_valid(self, form):
        form.instance.company = self.get_company()
        return super().form_valid(form)


class ProductRestockView(LoginRequiredMixin, FormView):
    """
    Formulario simplificado para recargar stock de un producto ya cargado:
    Cantidad, Proveedor y Precio de Costo (por defecto, el último cargado).
    """
    form_class = ProductRestockForm
    template_name = 'inventory/product_restock.html'
    success_url = reverse_lazy('dashboard')

    def get_company(self):
        user = self.request.user
        company = Company.objects.filter(owner=user).first()
        if not company:
            membership = user.memberships.filter(is_active=True).first()
            if membership:
                company = membership.company
        return company

    def get_product(self):
        return get_object_or_404(Product, pk=self.kwargs['pk'], company=self.get_company())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['company'] = self.get_company()
        kwargs['product'] = self.get_product()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = self.get_company()
        context['product'] = self.get_product()
        return context

    def form_valid(self, form):
        company = self.get_company()
        product = self.get_product()

        quantity = form.cleaned_data['quantity']
        provider = form.cleaned_data['provider']
        cost_price = form.cleaned_data['cost_price']

        # Actualizamos el proveedor y precio de costo del producto si cambiaron
        product.provider = provider
        product.cost_price = cost_price
        product.save(update_fields=['provider', 'cost_price'])

        default_warehouse = Warehouse.objects.filter(company=company).first()
        if default_warehouse:
            stock, created = WarehouseStock.objects.get_or_create(
                product=product,
                warehouse=default_warehouse,
                defaults={'quantity': quantity}
            )
            if not created:
                stock.quantity += quantity
                stock.save(update_fields=['quantity'])

            StockMovement.objects.create(
                company=company,
                product=product,
                warehouse=default_warehouse,
                movement_type='in',
                quantity=quantity,
                user=self.request.user,
                reason=f'Recarga de stock - Proveedor: {provider.name}'
            )

        provider.last_purchase = timezone.now()
        provider.save(update_fields=['last_purchase'])

        return super().form_valid(form)


