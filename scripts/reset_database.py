#!/usr/bin/env python
"""
Script para resetear la base de datos SQLite y crear un superusuario
"""
import os
import sys
import subprocess

def run_command(command, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    print("🔄 Reseteando base de datos SQLite...")
    
    # Obtener el directorio del proyecto
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    
    # Verificar que existe el archivo de base de datos
    db_file = os.path.join(project_dir, 'db.sqlite3')
    
    # Eliminar la base de datos si existe
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print("✅ Base de datos SQLite eliminada")
        except Exception as e:
            print(f"❌ Error al eliminar base de datos: {e}")
            return False
    else:
        print("ℹ️  No existe base de datos SQLite previa")
    
    # Activar el entorno virtual y ejecutar migraciones
    venv_python = os.path.join(project_dir, '.venv', 'bin', 'python')
    
    # Verificar que existe el entorno virtual
    if not os.path.exists(venv_python):
        print("❌ No se encontró el entorno virtual .venv")
        print("   Ejecuta primero: python3 -m venv .venv")
        return False
    
    # Ejecutar migraciones
    migrate_command = f"{venv_python} manage.py migrate"
    if not run_command(migrate_command, "Ejecutando migraciones"):
        return False
    
    print("✅ Base de datos creada y migraciones aplicadas")
    
    # Crear superusuario
    print("👤 Creando superusuario...")
    
    # Crear superusuario usando Django shell
    create_superuser_script = '''
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Crear superusuario
user, created = User.objects.get_or_create(
    username="admin",
    defaults={
        "email": "admin@example.com",
        "is_staff": True,
        "is_superuser": True,
        "is_active": True
    }
)

if created:
    user.set_password("admin123")
    user.save()
    print("✅ Superusuario creado:")
    print("   - Usuario: admin")
    print("   - Contraseña: admin123")
    print("   - Email: admin@example.com")
else:
    user.set_password("admin123")
    user.save()
    print("ℹ️  Superusuario ya existía, contraseña actualizada:")
    print("   - Usuario: admin")
    print("   - Contraseña: admin123")
'''
    
    # Ejecutar el script de creación de superusuario
    shell_command = f'{venv_python} -c "{create_superuser_script}"'
    if not run_command(shell_command, "Creando superusuario"):
        return False
    
    print("\n🎉 Reset de base de datos completado exitosamente!")
    print("\n📋 Próximos pasos:")
    print("   1. Ejecuta: python scripts/setup_projects_modules.py")
    print("   2. Ejecuta: python scripts/setup_sales_modules.py")
    print("   3. Inicia el servidor: python manage.py runserver")
    print("\n🔑 Credenciales de acceso:")
    print("   - Usuario: admin")
    print("   - Contraseña: admin123")

if __name__ == "__main__":
    main()