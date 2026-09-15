from .forms import UserRegistrationForm, UserLoginForm, CompanyRegistrationForm, ProductForm, ProviderForm, ProductRestockForm
from .models import Product, WarehouseTransfer, Company, User, Warehouse, Membership, WarehouseStock, UnitOfMeasure, StockMovement, Provider, Brand
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView, CreateView, FormView
from django.views.generic.edit import CreateView
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
import csv
import io
from decimal import Decimal, InvalidOperation
User = get_user_model()

# ================== ENCABEZADO DEL CSV ================== #
# Se usan tanto para generar la plantilla 'ejemplo' como para leer el archivo que sube el usuario #

PRODUCT_CSV_HEADERS = [
    'Categoría (Opcional)',
    'SKU / Código Interno',
    'Código de Barras / EAN (Opcional)',
    'Marca (Opcional)',
    'Proveedor (Opcional)',
    'Unidad de Medida (UN por default)',
    'Precio de Costo',
    'Stock Inicial',
    'Precio Ventas',
    'Nivel Mínimo de Stock',
    'Descripción (opcional)',
]


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


class ProductCSVSampleView(LoginRequiredMixin, View):
    """
    Descarga un CSV vacío (solo con los encabezados) para que el usuario
    lo complete offline y lo vuelva a subir en ProductCSVImportView.
    """
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="stockv_productos_sample.csv"'
        # BOM para que Excel abra los acentos correctamente
        response.write('﻿')
        writer = csv.writer(response)
        writer.writerow(PRODUCT_CSV_HEADERS)
        return response


class ProductCSVImportView(LoginRequiredMixin, TemplateView):
    """
    Carga masiva de productos a partir del CSV completado por el usuario.
    Cada fila se procesa de forma independiente: si una fila tiene un error,
    se informa y se sigue con las siguientes en vez de abortar todo el archivo.
    """
    template_name = 'inventory/product_csv_import.html'

    def get_company(self):
        user = self.request.user
        company = Company.objects.filter(owner=user).first()
        if not company:
            membership = user.memberships.filter(is_active=True).first()
            if membership:
                company = membership.company
        return company

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company'] = self.get_company()
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        company = context['company']

        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            context['results'] = {'created': 0, 'errors': [{'row': '-', 'message': 'No se seleccionó ningún archivo.'}]}
            return self.render_to_response(context)

        if not csv_file.name.lower().endswith('.csv'):
            context['results'] = {'created': 0, 'errors': [{'row': '-', 'message': 'El archivo debe tener extensión .csv'}]}
            return self.render_to_response(context)

        try:
            raw = csv_file.read()
            try:
                decoded = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                decoded = raw.decode('latin-1')
        except Exception:
            context['results'] = {'created': 0, 'errors': [{'row': '-', 'message': 'No se pudo leer el archivo.'}]}
            return self.render_to_response(context)

        # Excel en español suele exportar CSV separado por ";" en vez de ",".
        try:
            dialect = csv.Sniffer().sniff(decoded[:2048], delimiters=',;')
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
        reader.fieldnames = [(h or '').strip() for h in reader.fieldnames or []]

        context['results'] = self._import_rows(reader, company, request.user)
        return self.render_to_response(context)

    def _import_rows(self, reader, company, user):
        created = 0
        errors = []

        default_warehouse = Warehouse.objects.filter(company=company).first()
        uom_default, _ = UnitOfMeasure.objects.get_or_create(
            company=company, name="Unidades", defaults={'abbreviation': 'UN'}
        )

        for line_number, row in enumerate(reader, start=2):  # la fila 1 es el encabezado
            if not any((value or '').strip() for value in row.values()):
                continue  # fila vacía (común al final de un export de Excel)

            def get(column):
                return (row.get(column) or '').strip()

            sku = get('SKU / Código Interno')
            if not sku:
                errors.append({'row': line_number, 'message': 'Falta el SKU / Código Interno.'})
                continue

            if Product.objects.filter(company=company, sku=sku).exists():
                errors.append({'row': line_number, 'message': f'Ya existe un producto con SKU "{sku}" en esta compañía.'})
                continue

            try:
                cost_price = Decimal(get('Precio de Costo').replace(',', '.') or '0')
                sale_price = Decimal(get('Precio Ventas').replace(',', '.') or '0')
            except InvalidOperation:
                errors.append({'row': line_number, 'message': 'Precio de Costo o Precio Ventas inválido.'})
                continue

            try:
                min_stock_level = int(get('Nivel Mínimo de Stock') or 0)
            except ValueError:
                errors.append({'row': line_number, 'message': 'Nivel Mínimo de Stock inválido.'})
                continue

            try:
                initial_stock = int(get('Stock Inicial') or 0)
            except ValueError:
                errors.append({'row': line_number, 'message': 'Stock Inicial inválido.'})
                continue

            try:
                with transaction.atomic():
                    brand = None
                    brand_name = get('Marca (Opcional)')
                    if brand_name:
                        brand, _ = Brand.objects.get_or_create(company=company, name=brand_name)

                    provider = None
                    provider_name = get('Proveedor (Opcional)')
                    if provider_name:
                        provider, _ = Provider.objects.get_or_create(company=company, name=provider_name)

                    uom_name = get('Unidad de Medida (UN por default)')
                    if uom_name:
                        uom = (
                            UnitOfMeasure.objects.filter(company=company, abbreviation__iexact=uom_name).first()
                            or UnitOfMeasure.objects.filter(company=company, name__iexact=uom_name).first()
                        )
                        if not uom:
                            uom = UnitOfMeasure.objects.create(
                                company=company, name=uom_name, abbreviation=uom_name.upper()[:10]
                            )
                    else:
                        uom = uom_default

                    product = Product.objects.create(
                        company=company,
                        name=get('Categoría (Opcional)') or sku,
                        sku=sku,
                        barcode=get('Código de Barras / EAN (Opcional)') or None,
                        brand=brand,
                        provider=provider,
                        uom=uom,
                        cost_price=cost_price,
                        sale_price=sale_price,
                        min_stock_level=min_stock_level,
                        description=get('Descripción opcional') or None,
                    )

                    if default_warehouse and initial_stock > 0:
                        WarehouseStock.objects.get_or_create(
                            product=product,
                            warehouse=default_warehouse,
                            defaults={'quantity': initial_stock}
                        )
                        StockMovement.objects.create(
                            company=company,
                            product=product,
                            warehouse=default_warehouse,
                            movement_type='in',
                            quantity=initial_stock,
                            user=user,
                            reason='Importación CSV - Stock inicial',
                        )
            except Exception as exc:
                errors.append({'row': line_number, 'message': f'No se pudo crear el producto ({exc}).'})
                continue

            created += 1

        return {'created': created, 'errors': errors}

