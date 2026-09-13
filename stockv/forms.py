from django import forms
from .models import *
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()  ### llama al modelo User personalizado, no al default con AbstractUser

class UserRegistrationForm(UserCreationForm):
    """
    Formulario de registro de usuarios.
    Apunta al modelo User pero usa UserManager para crear.
    """
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'custom-input', 'placeholder': 'correo@ejemplo.com'})
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'custom-input', 'placeholder': 'Nombre'})
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'custom-input', 'placeholder': 'Apellido'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'custom-input', 'placeholder': 'Contraseña'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'custom-input', 'placeholder': 'Confirmar contraseña'})
    )
    
    class Meta:
        model = User  # ← Apunta al modelo User
        fields = ['email', 'first_name', 'last_name']
    
    def clean_email(self):
        """Validación personalizada para email único"""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este correo electrónico ya está registrado.')
        return email
    
    def save(self, commit=True):
        """
        Guarda el usuario usando el UserManager.
        El manager se encarga de la creación con email y first_name.
        """
        user = User.objects.create_user(  # ← Aquí usa UserManager
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data['first_name'],
            password=self.cleaned_data['password1'],
            last_name=self.cleaned_data['last_name'],
            # Puedes agregar más campos aquí
        )
        return user

class UserLoginForm(AuthenticationForm):
    """
    Formulario de Login
    """
    # Aunque el campo se llama 'username' (por compatibilidad interna de Django con el sistema de autenticación), el modelo User validará el correo electrónico gracias a USERNAME_FIELD = 'email'
    username = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'custom-input', 
            'placeholder': 'correo@ejemplo.com',
            # Con autofocus = True, cuando se cargue la página, el navegador coloca automáticamente el cursor en ese campo. Muuuy top!
            'autofocus': True
        })
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'custom-input', 
            'placeholder': '••••••••'
        })
    )

class CompanyRegistrationForm(forms.ModelForm):
    """
    Formulario para registro de empresas
    Es el primer paso que un nuevo usuario va a dar después de registrarse,
    para poder usar la plataforma.
    """
    class Meta:
        model = Company
        # Excluimos 'owner' porque lo asignaremos automáticamente desde la vista con el usuario logueado
        fields = ['name', 'tax_id', 'phone_number', 'website', 'address', 'city', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre comercial / Razón Social'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CUIT / RUT / NIT'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono de contacto'}),
            'website': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'www.tuempresa.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Dirección física', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class ProductForm(forms.ModelForm):
    initial_stock = forms.IntegerField(
        required=False,
        min_value=0,
        initial=0,
        label="Stock Inicial",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'})
    )
    
    field_order = [
        'name', 'sku', 'barcode', 'brand', 'provider', 'uom',
        'cost_price', 'initial_stock', 'sale_price',
        'min_stock_level', 'description', 'image',
    ]

    class Meta:
        model = Product
        # Excluimos campos calculados o que se asignan por lógica interna si corresponde
        fields = [
            'name', 'sku', 'barcode', 'brand', 'provider', 
            'uom', 'cost_price', 'sale_price', 'min_stock_level', 
            'description', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Categoría (Opcional)'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU / Código interno'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional'}),
            #'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.Select(attrs={'class': 'form-control'}),
            #'provider': forms.TextInput(attrs={'class': 'form-control'}),
            'provider': forms.Select(attrs={'class': 'form-control'}),
            #'uom': forms.TextInput(attrs={'class': 'form-control', 'required': False}),
            'uom': forms.Select(attrs={'class': 'form-control', 'required': False}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_stock_level': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripción opcional', 'rows': 3}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
    
    # necesito adaptar el formulario para los casos en que la empresa es nueva (todavía no existen marcas ni proveedores cargados). Para eso, 1. filtro los QuerySets por la compañía del usuario y hacer que esos campos sean opcionales en el formulario (required=False) y 2. asegurar que el sistema tenga al menos una Unidad de Medida por defecto, para que después el navegador no lo reclame.    
    def __init__(self, *args, **kwargs):
        # Extraemos la compañía que viene desde la vista
        company = kwargs.pop('company', None) # .pop elimina el valor a partir de la clave (y lo devuelve). Si no lo encuentra, devuelve None.
        super().__init__(*args, **kwargs)
        # De esta forma el argumento company queda disponible en la variable local company, pero no se pase hacia arriba cuando se llama a super().__init__(*args, **kwargs), evitando que la clase padre no recibe un argumento que no espera.

        if company:
            # 1. Creamos o recuperamos la unidad por defecto y la guardamos en una variable
            uom_default, created = UnitOfMeasure.objects.get_or_create(
                company=company,
                name="Unidades",
                defaults={'abbreviation': 'UN'}
            )

            # Filtramos los desplegables para que solo muestren datos de la empresa activa
            self.fields['brand'].queryset = Brand.objects.filter(company=company)
            self.fields['provider'].queryset = Provider.objects.filter(company=company)
            self.fields['uom'].queryset = UnitOfMeasure.objects.filter(company=company)

            # 3. Pre-seleccionamos la unidad por defecto para evitar el bloqueo del navegador
            if not self.initial.get('uom'):
                self.initial['uom'] = uom_default
            

        # Hacemos que marca y proveedor no sean obligatorios
        self.fields['brand'].required = False
        self.fields['brand'].empty_label = "Sin Marca (Opcional)"
        
        self.fields['provider'].required = False
        self.fields['provider'].empty_label = "Sin Proveedor (Opcional)"

