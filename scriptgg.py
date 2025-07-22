# EJECUTAR EN: python manage.py shell

# Script para verificar si los permisos existen
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.sales_team_management.models import EquipoVenta, Proyecto, Inmueble

print("🔍 Verificando permisos de sales...")

# Verificar content types
try:
    equipoventa_ct = ContentType.objects.get_for_model(EquipoVenta)
    print(f"✅ ContentType para EquipoVenta: {equipoventa_ct}")
except Exception as e:
    print(f"❌ Error con EquipoVenta ContentType: {e}")

try:
    proyecto_ct = ContentType.objects.get_for_model(Proyecto)
    print(f"✅ ContentType para Proyecto: {proyecto_ct}")
except Exception as e:
    print(f"❌ Error con Proyecto ContentType: {e}")

# Verificar permisos específicos
permisos_a_verificar = [
    'sales.add_equipoventa',
    'sales.change_equipoventa',
    'sales.delete_equipoventa',
    'sales.view_equipoventa',
    'sales.add_proyecto',
    'sales.change_proyecto',
    'sales.delete_proyecto',
    'sales.view_proyecto',
    'sales.add_inmueble',
    'sales.change_inmueble',
    'sales.delete_inmueble',
    'sales.view_inmueble',
]

print("\n📋 Verificando permisos específicos:")
for perm_code in permisos_a_verificar:
    app_label, codename = perm_code.split('.')
    try:
        permission = Permission.objects.get(
            content_type__app_label=app_label,
            codename=codename
        )
        print(f"✅ {perm_code}: {permission.name}")
    except Permission.DoesNotExist:
        print(f"❌ {perm_code}: NO EXISTE")

# Listar TODOS los permisos de sales
print("\n📦 Todos los permisos de sales:")
sales_permissions = Permission.objects.filter(content_type__app_label='sales')
for perm in sales_permissions:
    print(f"   • {perm.content_type.app_label}.{perm.codename}: {perm.name}")

print(f"\n📊 Total permisos de sales: {sales_permissions.count()}")

# Verificar si las tablas existen
from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'sales_%';")
tables = cursor.fetchall()
print(f"\n🗃️ Tablas de sales en la BD: {[table[0] for table in tables]}")

# Si no hay permisos, ejecutar:
if sales_permissions.count() == 0:
    print("\n🔧 SOLUCIÓN: Ejecuta estos comandos:")
    print("1. python manage.py migrate --run-syncdb")
    print("2. python manage.py fix_sales_permissions")
    print("3. python manage.py setup_sales_modules")
