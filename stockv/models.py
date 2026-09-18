from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.conf import settings
from django.utils.text import slugify
from decimal import Decimal
from django.db.models import Sum
from django.core.validators import MinValueValidator, MaxValueValidator

class UserManager(BaseUserManager):
    def create_user(self, email, first_name, password=None, **extra_fields):
        #Crea y guarda un usuario con el email, first_name, last_name y password.
        if not email:
            raise ValueError('El email es obligatorio')
        if not first_name:
            raise ValueError('El nombre es obligatorio')
        
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, first_name, password=None, **extra_fields):
        #Crea y guarda un superusuario con el email, first_name y password.
        # Como esto heredando de BaseUserManager, redefinimos los métodos para decirle a la base de datos que, cuando cree un usuario, se asegure que el email sea obligatorio (y lo pase a minúscula). Además, cuando cree un superusuario, asegurarse de que is_staff e is_superuser sean True obligatoriamente.
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # extra_fields.setdefault('user_type', 'admin')  # Valor por defecto para superuser
        
        # Validaciones para superusuario
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        
        return self.create_user(email, first_name, password, **extra_fields)


class User(AbstractUser):
	# --- autenticación ---
	username = None
	email = models.EmailField(unique=True, verbose_name='Correo Electrónico')

	# En este modelo User no vemos first_name ni last_name que se heredan con AbstractUser, que también gestiona create_user.

	# Los usuarios se van a loguear con su email.
	USERNAME_FIELD = 'email' # usa el campo email como identificador único para el login, en lugar del username por defecto.
	# El email ya es requerido por USERNAME_FIELD
	REQUIRED_FIELDS = ['first_name'] # lista de campos que (además del email) serán requeridos al crear el superusuario (con createsuperuser). En create_user en UserManager pido email, first_name y password, de modo que lo tengo que incluir cuando creo el superusuario.

	# Cuando creamos un modelo en Django, viene un manager por defecto llamado objects:
	# class User(AbstractUser):
	#     objects = models.Manager()  # ← Manager por defecto, sin necesidad de definir objects
	# Pero el UserManager que definí, sobrescribe el método create_user por defecto.

	# >> Manager por defecto:
	# 		User.objects.create_user(username="juan", email="juan@mail.com", password="123")

	# >> UserManager personalizado:
	# 		User.objects.create_user(email="juan@mail.com", first_name="Juan", password="123")

	# con objects = UserManager(), le indicamos a Django que cuando quiera crear, buscar o interactuar con usuarios, use las reglas definidas en UserManager, no las reglas por defecto.

	objects = UserManager()
 
	### Por ejemplo, si defino: REQUIRED_FIELDS = ['phone_number', 'address'], al ejecutar: python manage.py createsuperuser va a solicitar:
	### - Email (por USERNAME_FIELD)
	### - Phone number (por REQUIRED_FIELDS)
	### - Address (por REQUIRED_FIELDS)
	### - Password
	### En este caso, solo necesito el email y password (los demás son opcionales con blank=True, null=True), de modo que dejamos la lista vacía.

	# --- info personal y del negocio ---
	address = models.CharField(max_length=255, blank=True, null=True, verbose_name='Dirección')
	country = models.CharField(max_length=100, blank=True, null=True, verbose_name='Pais')
	phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Teléfono')
	city = models.CharField(max_length=100, blank=True, null=True, verbose_name='Ciudad')
	zip_code = models.CharField(max_length=10, blank=True, null=True, verbose_name='Código Postal')

	# --- social media ---
	x_url = models.URLField(max_length=200, blank=True, null=True, verbose_name='X (Twitter)')
	instagram_url = models.URLField(max_length=200, blank=True, null=True, verbose_name='Instagram')
	facebook_url = models.URLField(max_length=200, blank=True, null=True, verbose_name='Facebook')
									
	# --- permisos multitenant ---
	# is_staff: dueños de empresa (Owners), empleados y administrativos
	# is_superuser: administrador de la plataforma
	# ya vienen heredados de AbstractUser

	# --- status y logs ---
	last_active = models.DateTimeField(blank=True, null=True, verbose_name='Ultima Actividad')

	# --- terminos & notificaciones ---
	terms_accepted = models.BooleanField(default=False, verbose_name='Términos Aceptados')
	terms_accepted_at = models.DateTimeField(blank=True, null=True, verbose_name='Términos Aceptados con fecha')
	email_notifications_enabled = models.BooleanField(default=True, verbose_name='Notificaciones por Email Habilitadas')

	class Meta:
		verbose_name = 'Usuario'
		verbose_name_plural = 'Usuarios'
		indexes = [
			models.Index(fields=['email']), # indexa los usuarios por su email, facilita la búsqueda en el momento del loguin.
			#models.Index(fields=['is_verified']), # voy a necesitar filtrar usuarios verificados y no verificados con frecuencia
		]
	# __str__ define cómo se va a mostrar el objeto User cuando se convierta en un string x ej en el panel de administración de Django
	def __str__(self): 
		return f"{self.email} ({self.get_full_name() or 'Sin Nombre'})"


class Company(models.Model):
	# --- info básica ---
	name = models.CharField(max_length=200, verbose_name="Nombre Comercial")
	legal_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre Legal (Razón Social)")
	tax_id = models.CharField(max_length=50, unique=True, verbose_name="Tax ID (RUT/NIT/CUIT)")

	# --- contacto y facturación (para facturas y órdenes de compra) ---
	corporate_email = models.EmailField(verbose_name="Correo Corporativo")
	billing_email = models.EmailField(verbose_name="Billing email", help_text="Correo Administración")
	phone_number = models.CharField(max_length=20, verbose_name="Teléfono de Contacto")
	website = models.URLField(max_length=200, blank=True, null=True, verbose_name="Sitio Web")
	address = models.TextField(verbose_name="Dirección")
	city = models.CharField(max_length=100, verbose_name="Ciudad")
	logo = models.ImageField(default='companies/default_logo.jpg', upload_to='companies/logos/', verbose_name='Logo Empresa')

	# --- El creador/dueño de la empresa ---
	owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='owned_companies', verbose_name="Propietario")
	is_verified = models.BooleanField(default=False, verbose_name='Verified company', help_text='Indica si la empresa ha sido verificada manualmente por un administrador del sistema.')
	# --- planes de suscripción: no va a ser gratuito para siempre ---
	PLAN_CHOICES = [
		('basic', 'Básico'),
		('professional', 'Profesional'),
		('enterprise', 'Corporativo'),
	]
	plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='basic', verbose_name="Plan de Suscripción")
	is_active = models.BooleanField(default=True, verbose_name="Active", help_text="Indica si esta empresa tiene permiso para utilizar el sistema.")
	subscription_start = models.DateField(default=timezone.now, verbose_name="Fecha de Inicio de la Suscripción")
	subscription_end = models.DateField(null=True, blank=True, verbose_name="Fecha de Fin de la Suscripción")

	# --- infraestructura: subdominio para asegurar unicidad ---
	subdomain = models.SlugField(max_length=100, unique=True, null=True, blank=True, verbose_name="Subdominio")
	notes = models.TextField(blank=True, null=True, verbose_name="Información Adicional")

	# --- metadata ---
	created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creado") # la fecha se establece una sola vez, al crear el registro.
	updated_at = models.DateTimeField(auto_now=True, verbose_name="Actualizado") # la fecha se actualiza cada vez que se guarda el restistro

	## --- indexes vs. ordering --- ##
	# indexes - estructuras físicas en la base de datos: facilitan las búsquedas; no afecta los resultados mostrados
	# ordering - define el orden por defecto al recuperar datos; determina el orden en el que los resultados son mostrados
	
	class Meta:
		verbose_name = "Companía"
		verbose_name_plural = "Companias"
		ordering = ['name']

	def __str__(self):
		return self.name

	## -- chequeamos si la suscripción de la empresa sigue activa o ya venció -- ##
	## -- ventajas de @property -- ##
	# no ocupa espacio en DB
	# se calcula en tiempo real (cada vez que se lo invoca)
	# se mantiene siempre actualizado
	@property
	def is_subscription_valid(self):
		# Si la empresa tiene fecha de fin de suscripción
		if self.subscription_end:
			# comparamos con la fecha de hoy
			return self.subscription_end >= timezone.now().date()
			# Si no tiene fecha de fin (es decir, self.subscription_end está ´vacía), entonces la empresa es siempre válida
		return True


class Product(models.Model):
	# asociamos el producto a una company para que productos iguales no se mezclen entre empresas
	# usamos 'Company' (el nombre del modelo) entrecomillas, con el nombre del modelo como string, para no tener que importarlo.
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='products', verbose_name="Companía")
	name = models.CharField(max_length=255, verbose_name="Categoría")
	# SKU (Stock Keeping Unit), código interno único para identificar el producto, distinto al código de barras.
	sku = models.CharField(max_length=50, blank=True, null=True, verbose_name="SKU / Código Interno")
	barcode = models.CharField(max_length=100, blank=True, null=True, verbose_name="Código de Barras / EAN")
	# Relación con el futuro modelo de Proveedor
	provider = models.ForeignKey('Provider', on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name="Proveedor") 
	description = models.TextField(blank=True, null=True, verbose_name="Descripción") 
	image = models.ImageField(upload_to='products/', default='products/default_product.jpg', verbose_name="Foto del Producto") 
	cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Precio de Costo") 
	sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name="Precio Ventas")
	brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='Marca')
	uom = models.ForeignKey('UnitOfMeasure', on_delete=models.PROTECT, related_name='products', verbose_name="Unidad de Medida")
	min_stock_level = models.PositiveIntegerField(default=0, verbose_name="Nivel Mínimo de Stock", help_text="Cantidad mínima que debe haber en inventario antes de reabastecer")

	# usamos Sum, (importado al principio) y el modelo para depósitos
	@property
	def current_stock(self):
		result = self.warehouse_stocks.aggregate(
			total = Sum('quantity')
		)
		total = result['total']
		if total is not None:
			return total
		return 0

	# cuánto de ese stock ya está comprometido en ventas pendientes (todavía no confirmadas)
	@property
	def reserved_stock(self):
		result = self.sale_items.filter(sale__status='pending').aggregate(
			total = Sum('quantity')
		)
		total = result['total']
		if total is not None:
			return total
		return 0

	# lo que realmente se puede seguir vendiendo: físico menos reservado
	@property
	def available_stock(self):
		return self.current_stock - self.reserved_stock

	# verificamos nivel de stock
	@property
	def is_below_min_stock(self):
	# Variable de quiebre de stock: verifica si el total está por debajo del mínimo.
		#return self.current_stock < self.min_stock_level # compara y retorna True o False
		return self.available_stock < self.min_stock_level # compara y retorna True o False
  

	# --- status y tracking ---
	# usamos is_active para "borrar" lógicamente un producto sin perder el historial de pedidos asociados.
	is_active = models.BooleanField(default=True, verbose_name="Activo")
	created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha Creación")
	updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")

	class Meta:
		verbose_name = "Producto"
		verbose_name_plural = "Productos"
		ordering = ['name']
		constraints = [
			models.UniqueConstraint(
				fields=['company', 'sku'],
				name='unique_company_sku_name'
			),
		]
		# Optimizamos los índices
		indexes = [
			models.Index(fields=['company', 'brand']), # Búsqueda de marca dentro de la empresa
			models.Index(fields=['company', 'barcode']), # Búsqueda por lector de barras
		]

	# usamos el método __str__ para obtener "marca nombre" cuando existe la marca, y si no hay marca devuelve solo el nombre.
	def __str__(self):
		if self.brand:
			return f"{self.brand} {self.name}"
		else:
			return self.name


class Warehouse(models.Model):
	# --- identidad y multitenant ---
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='warehouses')
	name = models.CharField(max_length=100, verbose_name="Nombre del Depósito")
	code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Depósito Código Interno")

	# --- ubicación ---
	address = models.TextField(verbose_name="Dirección")
	city = models.CharField(max_length=100, verbose_name="Ciudad")
	state_province = models.CharField(max_length=100, verbose_name="Departamento / Provincia")
	zip_code = models.CharField(max_length=15, blank=True, null=True, verbose_name="Código Postal")

	# --- administración ---
	manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_warehouses', verbose_name="Gerente")
	capacity = models.PositiveIntegerField(blank=True, null=True, verbose_name="Capacity", help_text="Capacidad de Almacenamiento en Unidades o Volumen")

	# --- status e información ---
	is_active = models.BooleanField(default=True, verbose_name="Activo")
	notes = models.TextField(blank=True, null=True, verbose_name="Notas Internas")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Depósito"
		verbose_name_plural = "Depósitos"
		# Unicidad: No puede haber dos depósitos con el mismo nombre o código EN LA MISMA empresa
		# La estructura (('company', 'name'), ('company', 'code')) define dos reglas de unicidad independientes:
		# 1- ('company', 'name'): Ninguna empresa puede tener dos depósitos con el mismo nombre pero 2 empresas distintas pueden tener un depósito llamado igual y
		# 2 ('company', 'code'): Ninguna empresa puede repetir un código interno (ej: "DEP-01").
		# Pero la Empresa A y la Empresa B pueden usar ambas el código "DEP-01" sin problemas.
		constraints = [
			models.UniqueConstraint(
				fields=['company', 'name'],
				name='unique_company_name_warehouse'
			),
			models.UniqueConstraint(
				fields=['company', 'code'],
				name='unique_company_code_warehouse'
			),
		]
		ordering = ['name']

	def __str__(self):
		return f"{self.name} ({self.city})"


class Membership(models.Model):
	ROLE_CHOICES = [
		('owner', 'Propietario'),
		('admin', 'Administrador'),
		('warehouse_staff', 'Personal de Depósito'),
		('sales', 'Ventas'),
	]
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memberships')
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='memberships')
	role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='warehouse_staff')
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
			fields=['user', 'company'], 
			name='unique_user_company_membership')
		]

	def __str__(self):
		return f"{self.user.email} @ {self.company.name} ({self.role})"


class WarehouseStock(models.Model):
    # El modelo WarehouseStock vincula Producto y Depósito para saber cuanto stock hay en cada lugar: un producto puede estar en muchos depósitos, y un depósito tener muchos productos.
	# --- vinculamos el producto y el depósito ---
	product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='warehouse_stocks')
	warehouse = models.ForeignKey('Warehouse', on_delete=models.CASCADE, related_name='product_stocks')
	# --- cantidades: PositiveIntegerField nos asegura que no haya stock negativo accidental ---
	quantity = models.PositiveIntegerField(default=0, verbose_name="Quantity in stock")
	# --- ubicación física ---
	aisle = models.CharField(max_length=50, blank=True, null=True, verbose_name="Pasillo")
	shelf = models.CharField(max_length=50, blank=True, null=True, verbose_name="Estantería")
	bin_rack = models.CharField(max_length=50, blank=True, null=True, verbose_name="Contenedor / Rack")

	# --- inventario manual ---
	last_inventory_check = models.DateTimeField(blank=True, null=True, verbose_name="Ultimo Inventario Manual")
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Stock en Depósito"
		verbose_name_plural = "Stocks en Depósito"
		# solo UN registro por producto+almacén (no puedes tener dos stocks del mismo producto en el mismo almacén)
		constraints = [
			models.UniqueConstraint(
				fields=['product', 'warehouse'],
				name='unique_product_warehouse_warehousestock'
			),
		]
	def __str__(self):
		return f"{self.product.name} in {self.warehouse.name}: {self.quantity}"


class StockMovement(models.Model):
	MOVEMENT_TYPES = [
		('in', 'Ingreso'),
		('out', 'Egreso'),
		('transfer', 'Transferencia entre Depósitos'),
		('adjustment', 'Ajuste Manual'),
		]
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='stock_movements')
	product = models.ForeignKey('Product', on_delete=models.CASCADE)
	# Desde dónde sale o hacia dónde entra
	warehouse = models.ForeignKey('Warehouse', on_delete=models.CASCADE)
	movement_type = models.CharField(max_length=15, choices=MOVEMENT_TYPES)
	quantity = models.IntegerField()  # Positivo para entradas, negativo para salidas
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
	reason = models.CharField(max_length=255, blank=True, null=True) # Ej: "Compra factura #123"
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Stock movement"


class Brand(models.Model):
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='brands')
	name = models.CharField(max_length=100, verbose_name="Marca")
	logo = models.ImageField(upload_to='brands/', blank=True, null=True, verbose_name="Logo")
	description = models.TextField(blank=True, null=True, verbose_name="Descripción")

	class Meta:
		constraints = [
		models.UniqueConstraint(
			fields=['company', 'name'],
			name='unique_company_name_brand'
			)
		]
		verbose_name = "Marca"
		verbose_name_plural = "Marcas"

	def __str__(self):
		return self.name


class UnitOfMeasure(models.Model):
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='units')
	name = models.CharField(max_length=50, verbose_name="Unit name") # Ej: Kilogramos
	abbreviation = models.CharField(max_length=10, verbose_name="Abbreviation") # Ej: kg

	class Meta:
		constraints = [
		models.UniqueConstraint(
			fields=['company', 'name'],
			name='unique_company_name_uom'
			)
		]
		verbose_name = "Unidad de Medida"
		verbose_name_plural = "Unidades de Medida"

	def __str__(self):
		return f"{self.name} ({self.abbreviation})"


class WarehouseTransfer(models.Model):
    # involucra un origen y un destino, lo usamos para no perder el rastro de la mercadería "en tránsito"
	STATUS_CHOICES = [
		('pending', 'Pending'),
		('in_transit', 'In Transit'),
		('completed', 'Completed'),
		('cancelled', 'Cancelled'),
		]

	company = models.ForeignKey('Company', on_delete=models.CASCADE)
	product = models.ForeignKey('Product', on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField()
	origin_warehouse = models.ForeignKey('Warehouse', on_delete=models.CASCADE, related_name='outgoing_transfers')
	destination_warehouse = models.ForeignKey('Warehouse', on_delete=models.CASCADE, related_name='incoming_transfers')
	status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
	transfer_date = models.DateTimeField(auto_now_add=True)
	received_at = models.DateTimeField(blank=True, null=True)

	class Meta:
		verbose_name = "Transferencia entre Depósitos"
		verbose_name_plural = "Transferencias entre Depósitos"

	def __str__(self):
		return f"Transfer: {self.product.name} from {self.origin_warehouse.name} to {self.destination_warehouse.name}"


class Return(models.Model):
    # el campo condition en Devoluciones: si un producto vuelve "Damaged", el sistema no debería sumarlo al stock disponible sino a un stock de mermas o pérdida.
	# Seguridad: El modelo de Warranty permite verificar rápidamente si un cliente todavía tiene derecho a un cambio.
	CONDITION_CHOICES = [
		('new', 'Nuevo'),
		('damaged', 'Dañado'),
		('opened', 'Caja Abierta'),
		]

	company = models.ForeignKey('Company', on_delete=models.CASCADE)
	product = models.ForeignKey('Product', on_delete=models.CASCADE)
	warehouse = models.ForeignKey('Warehouse', on_delete=models.CASCADE) # A dónde vuelve
	# relación opcional con Warranty
	warranty = models.ForeignKey('Warranty', on_delete=models.SET_NULL, null=True, blank=True, related_name='returns',verbose_name="Garantía Asociada")
	quantity = models.PositiveIntegerField()
	reason = models.TextField(verbose_name="Motivos de la Devolución")
	condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='opened')

	# Vinculación con quién lo procesó
	processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Devolución"
		verbose_name_plural = "Devoluciones"

	def __str__(self):
		return f"Return: {self.product.name} ({self.quantity})"

	@property
	def is_covered_by_warranty(self):
		"""Retorna True si la devolución está vinculada a una garantía válida y no expirada."""
		if self.warranty:
			return not self.warranty.is_expired and self.warranty.is_active
		return False


class Warranty(models.Model):
	# Este modelo es funciona si se ofrecen productos con números de serie o que requieren un seguimiento post-venta.
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='warranties')
	product = models.ForeignKey('Product', on_delete=models.CASCADE)
	# Podemos asociarlo a una empresa cliente o un número de factura
	reference_number = models.CharField(max_length=100, verbose_name="Número de Factura")
	serial_number = models.CharField(max_length=100, blank=True, null=True)
	start_date = models.DateField(verbose_name="Inicio de la Garantía")
	end_date = models.DateField(verbose_name="Fecha de Caducidad de la Garantía")
	notes = models.TextField(blank=True, null=True)
	is_active = models.BooleanField(default=True)

	class Meta:
		verbose_name = "Garantía"
		verbose_name_plural = "Garantías"

	# usa timezone (importada antes) para determinar si la garantía expiró
	@property
	def is_expired(self):
		return self.end_date < timezone.now().date()


class Provider(models.Model):
    # --- MODELO PROVEEDORES: identidad y multitenant ---
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='providers')
	name = models.CharField(max_length=200, verbose_name="Nombre del Proveedor")
	code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código de Proveedor") # código interno
	tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="RUT / NIT / CUIT", help_text="Identificación Tributaria del Proveedor")
	contact_person = models.CharField(max_length=100, blank=True, null=True, verbose_name="Persona de Contacto")
	email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
	phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
	mobile = models.CharField(max_length=20, blank=True, null=True, verbose_name="Celular")
	website = models.URLField(max_length=200, blank=True, null=True, verbose_name="Sitio Web")
	address = models.TextField(blank=True, null=True, verbose_name="Dirección")
	city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ciudad")
	state_province = models.CharField(max_length=100, blank=True, null=True, verbose_name="Departamento / Provincia")
	country = models.CharField(max_length=100, blank=True, null=True, verbose_name="País")
	zip_code = models.CharField(max_length=15, blank=True, null=True, verbose_name="Código Postal")

    # --- tipo de proveedor ---
	provider_type = models.CharField(
		max_length=50,
		choices=[
			('LOCAL', 'Local'),
			('NATIONAL', 'Nacional'),
			('INTERNATIONAL', 'Internacional'),
			('DISTRIBUTOR', 'Distribuidor'),
			('MANUFACTURER', 'Fabricante'),
			('WHOLESALER', 'Mayorista'),
		],
		default='LOCAL',
		verbose_name="Tipo de Proveedor"
	)

	# condiciones de pago
	payment_terms = models.CharField(max_length=100, blank=True, null=True, verbose_name="Condiciones de Pago", help_text="Ej: 30 días, 60 días, contado, etc.")

	# límite de crédito
	credit_limit = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True, verbose_name="Límite de Crédito", help_text="Monto máximo de crédito otorgado")

    # --- Moneda ---
	currency = models.CharField(
		max_length=3,
		choices=[
			('UYU', 'Peso Uruguayo'),
			('USD', 'Dólar'),
			('EUR', 'Euro'),
			('ARS', 'Peso Argentino'),
			('MXN', 'Peso Mexicano'),
			('COP', 'Peso Colombiano'),
			('CLP', 'Peso Chileno'),
			('PEN', 'Sol Peruano'),
		],
		default='USD',
		verbose_name="Moneda"
	)

    # --- rating y evaluación ---
	rating = models.PositiveSmallIntegerField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name="Calificación", help_text="Calificación del proveedor del 1 al 5")
	is_preferred = models.BooleanField(default=False, verbose_name="Proveedor Preferente")
	is_verified = models.BooleanField(default=False, verbose_name="Proveedor Verificado", help_text="Indica si el proveedor ha sido verificado por la empresa")
	main_products = models.TextField(blank=True, null=True, verbose_name="Productos/Servicios Principales", help_text="Principales productos o servicios que ofrece")
	account_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_providers', verbose_name="Ejecutivo de Cuenta", help_text="Persona responsable de la relación con este proveedor")
	warehouses = models.ManyToManyField('Warehouse', blank=True, related_name='providers', verbose_name="Depósitos Asociados")

    # --- status y logs ---
	is_active = models.BooleanField(default=True, verbose_name="Activo")
	notes = models.TextField(blank=True, null=True, verbose_name="Notas Internas")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	last_purchase = models.DateTimeField(
		blank=True,
		null=True,
		verbose_name="Última Compra"
	)

	class Meta:
		verbose_name = "Proveedor"
		verbose_name_plural = "Proveedores"
		
		# Restricciones de unicidad multitenant
		constraints = [
			models.UniqueConstraint(
				fields=['company', 'name'],
				name='unique_company_provider_name'
			),
			models.UniqueConstraint(
				fields=['company', 'code'],
				name='unique_company_provider_code'
			),
			models.UniqueConstraint(
				fields=['company', 'tax_id'],
				name='unique_company_provider_tax_id',
				condition=models.Q(tax_id__isnull=False)  # Solo si tax_id no es null
			),
		]
        
		ordering = ['name']
		indexes = [
			models.Index(fields=['company', 'is_active']),
			models.Index(fields=['company', 'is_preferred']),
			models.Index(fields=['company', 'rating']),
		]

	def __str__(self):
		return f"{self.name} ({self.code or 'Sin Código'})"

	def get_full_contact(self):
		"""Retorna la información de contacto completa"""
		contact_parts = []
		if self.contact_person:
			contact_parts.append(f"Contacto: {self.contact_person}")
		if self.phone:
			contact_parts.append(f"Tel: {self.phone}")
		if self.email:
			contact_parts.append(f"Email: {self.email}")
		return " | ".join(contact_parts) if contact_parts else "Sin contacto"

	def is_credit_available(self, amount):
		"""Verifica si el proveedor tiene crédito disponible"""
		if self.credit_limit is None:
			return True  # Sin límite de crédito
		# Asumiendo que tienes un método para obtener el crédito usado
		# credit_used = self.get_credit_used()
		# return (self.credit_limit - credit_used) >= amount
		return True  # Placeholder


class Customer(models.Model):
	# --- MODELO CLIENTES: identidad y multitenant ---
	# Versión liviana a propósito (a diferencia de Provider): se agrega ahora para no
	# tener que migrar Sale más adelante, aunque todavía no se use mucho.
	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='customers')
	name = models.CharField(max_length=200, verbose_name="Nombre del Cliente")
	code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Código de Cliente")
	tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="RUT / NIT / CUIT")
	email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
	phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
	address = models.TextField(blank=True, null=True, verbose_name="Dirección")
	city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ciudad")

	# --- status y logs ---
	is_active = models.BooleanField(default=True, verbose_name="Activo")
	notes = models.TextField(blank=True, null=True, verbose_name="Notas Internas")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Cliente"
		verbose_name_plural = "Clientes"
		constraints = [
			models.UniqueConstraint(
				fields=['company', 'name'],
				name='unique_company_customer_name'
			),
			models.UniqueConstraint(
				fields=['company', 'tax_id'],
				name='unique_company_customer_tax_id',
				condition=models.Q(tax_id__isnull=False)  # Solo si tax_id no es null
			),
		]
		ordering = ['name']

	def __str__(self):
		return self.name


class Sale(models.Model):
	# --- MODELO VENTAS: cabecera del pedido/ticket ---
	# 'pending'   -> reserva stock (cuenta en Product.reserved_stock) pero todavía no lo descuenta
	# 'confirmed' -> ya se descontó WarehouseStock y se generó el StockMovement de salida
	# 'cancelled' -> se liberó la reserva sin tocar stock físico (nunca llegó a descontarse)
	STATUS_CHOICES = [
		('pending', 'Pendiente'),
		('confirmed', 'Confirmada'),
		('cancelled', 'Cancelada'),
	]

	company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='sales')
	# PROTECT: no queremos perder el historial de ventas si se borra un depósito
	warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT, related_name='sales', verbose_name="Depósito")
	customer = models.ForeignKey('Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='sales', verbose_name="Cliente")
	status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name="Estado")

	created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='sales_created', verbose_name="Cargada por")
	created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
	confirmed_at = models.DateTimeField(blank=True, null=True, verbose_name="Fecha de Confirmación")
	updated_at = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
	notes = models.TextField(blank=True, null=True, verbose_name="Notas")

	class Meta:
		verbose_name = "Venta"
		verbose_name_plural = "Ventas"
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['company', 'status']),
		]

	def __str__(self):
		return f"Venta #{self.pk or 'sin guardar'} ({self.get_status_display()})"

	# El total se calcula a partir de las líneas, nunca se guarda en un campo:
	# así nunca puede desincronizarse de lo que realmente está cargado en la venta.
	@property
	def total(self):
		return sum((item.subtotal for item in self.items.all()), Decimal('0.00'))


class SaleItem(models.Model):
	# --- MODELO VENTAS: líneas del pedido/ticket ---
	sale = models.ForeignKey('Sale', on_delete=models.CASCADE, related_name='items')
	# PROTECT: no queremos perder el historial de ventas si se borra un producto
	product = models.ForeignKey('Product', on_delete=models.PROTECT, related_name='sale_items')
	quantity = models.PositiveIntegerField(verbose_name="Cantidad")
	# Precio al momento de la venta: NO se referencia product.sale_price en vivo,
	# porque si el precio cambia después no queremos reescribir ventas ya cargadas.
	unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio Unitario")

	class Meta:
		verbose_name = "Línea de Venta"
		verbose_name_plural = "Líneas de Venta"
		constraints = [
			models.UniqueConstraint(
				fields=['sale', 'product'],
				name='unique_sale_product'
			),
		]

	def __str__(self):
		return f"{self.product.name} x{self.quantity} en Venta #{self.sale_id}"

	@property
	def subtotal(self):
		return self.quantity * self.unit_price
