from django.contrib import admin
from .models import User, Company

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


admin.site.register(User, UsersAdmin)
admin.site.register(Company, CompanyAdmin)

# admin site personalizado
admin.site.site_header = "StockV :: Panel de Control"
admin.site.site_title = "StockV"
admin.site.index_title = "Panel de Administración"