#!/usr/bin/env python
"""
Script para resetear la base de datos SQLite y crear un superusuario (versión arreglada)
"""
import os
import sys

def main():
    print("🔄 Reseteando base de datos SQLite...")
    
    # Obtener el directorio del proyecto
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_dir)
    
    # Eliminar la base de datos si existe
    db_file = os.path.join(project_dir, 'db.sqlite3')
    
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
            print("✅ Base de datos SQLite eliminada")
        except Exception as e:
            print(f"❌ Error al eliminar base de datos: {e}")
            return False
    else:
        print("ℹ️  No existe base de datos SQLite previa")
    
    # Configurar Django directamente en el script
    sys.path.append(project_dir)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    
    try:
        import django
        django.setup()
    except ImportError as e:
        print(f"❌ Error al configurar Django: {e}")
        print("   Asegúrate de estar en el entorno virtual correcto")
        return False
    
    print("🔄 Ejecutando migraciones...")
    
    try:
        from django.core.management import execute_from_command_line
        
        # Ejecutar migraciones
        sys.argv = ['manage.py', 'migrate']
        execute_from_command_line(sys.argv)
        
        print("✅ Migraciones aplicadas exitosamente")
        
    except Exception as e:
        print(f"❌ Error en migraciones: {e}")
        return False
    
    # Crear superusuario
    print("👤 Creando superusuario...")
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Crear superusuario
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@korban.com", 
                "is_staff": True,
                "is_superuser": True,
                "is_active": True
            }
        )
        
        if created:
            user.set_password("admin123")
            user.save()
            print("✅ Superusuario creado:")
        else:
            user.set_password("admin123")
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            print("ℹ️  Superusuario actualizado:")
        
        print("   - Usuario: admin")
        print("   - Contraseña: admin123")
        print("   - Email: admin@korban.com")
        
    except Exception as e:
        print(f"❌ Error creando superusuario: {e}")
        return False
    
    print("\n🎉 Reset de base de datos completado exitosamente!")
    print("\n📋 Próximos pasos:")
    print("   1. Ejecuta: python scripts/setup_projects_modules.py")
    print("   2. Inicia el servidor: python manage.py runserver")
    print("\n🔑 Credenciales de acceso:")
    print("   - Usuario: admin")
    print("   - Contraseña: admin123")
    print("   - URL: http://127.0.0.1:8000/accounts/login/")

if __name__ == "__main__":
    main()