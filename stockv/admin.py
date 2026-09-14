from datetime import timedelta

from django.contrib import admin
from django.utils import timezone

from .models import User, Company, Provider, Product


## ============== PROVEEDORES (listado dentro de cada Compañía) ============== ##
class ProviderInline(admin.TabularInline):
    model = Provider
    verbose_name_plural = 'Proveedores de esta compañía'
    extra = 0
    fields = ('name', 'code', 'provider_type', 'contact_person', 'phone', 'is_active', 'is_preferred')
    readonly_fields = fields
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


## ============== USUARIOS ============== ##
class UsersAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'first_name',
        'last_name',
        'last_active',
        'company',
        'is_staff',
        )
    # verbose_name = 'Usuuarios'
    @admin.display(description='Compañía')
    def company(self, obj):
        membership = obj.memberships.first()

        if membership:
            return membership.company

        return '-.-'

## ============== COMPAÑÍAS ============== ##
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'owner',
        'address',
        'city',
    )
    inlines = [ProviderInline]


admin.site.register(User, UsersAdmin)
admin.site.register(Company, CompanyAdmin)

# admin site personalizado
admin.site.site_header = "StockV :: Panel de Control"
admin.site.site_title = "StockV"
admin.site.index_title = "Panel de Administración"


## ============== TABLERO / DASHBOARD ============== ##
def _new_since(queryset, date_field, days):
    """Cuenta cuántos registros del queryset se crearon en los últimos `days` días."""
    since = timezone.now() - timedelta(days=days)
    return queryset.filter(**{f'{date_field}__gte': since}).count()


def get_dashboard_stats():
    now = timezone.now()

    users_qs = User.objects.all()
    products_qs = Product.objects.filter(is_active=True)
    providers_qs = Provider.objects.filter(is_active=True)

    return {
        'total_users': users_qs.count(),
        'new_users_7d': _new_since(users_qs, 'date_joined', 7),
        'new_users_30d': _new_since(users_qs, 'date_joined', 30),

        # No existe un log histórico de accesos: se cuentan los usuarios cuyo
        # último login (last_active) cayó dentro de los últimos 7 días.
        'accesses_7d': users_qs.filter(last_active__gte=now - timedelta(days=7)).count(),

        'total_products': products_qs.count(),
        'new_products_7d': _new_since(products_qs, 'created_at', 7),
        'new_products_30d': _new_since(products_qs, 'created_at', 30),

        'total_providers': providers_qs.count(),
        'new_providers_7d': _new_since(providers_qs, 'created_at', 7),
        'new_providers_30d': _new_since(providers_qs, 'created_at', 30),
    }


# Inyectamos las estadísticas en el índice del admin sin reemplazar la vista completa.
_original_index = admin.site.index

def _index_with_dashboard(request, extra_context=None):
    extra_context = extra_context or {}
    extra_context['dashboard_stats'] = get_dashboard_stats()
    return _original_index(request, extra_context)

admin.site.index = _index_with_dashboard
