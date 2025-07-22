#!/usr/bin/env python
"""
Script minimalista para resetear la base de datos sin channels
Solo para crear roles y usuarios
"""
import os
import sys

def main():
    print("🔄 Reset minimalista para roles y usuarios...")
    
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
    
    # Configurar Django con apps mínimas
    sys.path.append(project_dir)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scripts.minimal_settings')
    
    try:
        import django
        django.setup()
        print("✅ Django configurado exitosamente")
    except ImportError as e:
        print(f"❌ Error al configurar Django: {e}")
        return False
    
    print("🔄 Ejecutando migraciones...")
    
    try:
        from django.core.management import execute_from_command_line
        
        # Ejecutar migraciones solo para apps básicas
        original_argv = sys.argv[:]
        sys.argv = ['manage.py', 'migrate']
        execute_from_command_line(sys.argv)
        sys.argv = original_argv
        
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
        
        user.set_password("admin123")
        user.save()
        
        status = "✅ Superusuario creado:" if created else "ℹ️ Superusuario actualizado:"
        print(status)
        print("   - Usuario: admin")
        print("   - Contraseña: admin123")
        print("   - Email: admin@korban.com")
        
    except Exception as e:
        print(f"❌ Error creando superusuario: {e}")
        return False
    
    # Verificar que los modelos de accounts existan
    try:
        from apps.accounts.models import Role, MenuCategory
        print("✅ Modelos de accounts disponibles")
        
        # Verificar tablas
        from django.db import connection
        tables = connection.introspection.table_names()
        accounts_tables = [t for t in tables if 'accounts' in t]
        print(f"✅ Tablas de accounts creadas: {len(accounts_tables)}")
        
    except Exception as e:
        print(f"⚠️  Advertencia con modelos accounts: {e}")
    
    print("\n🎉 Reset minimalista completado exitosamente!")
    print("\n📋 Ahora puedes:")
    print("   1. Crear roles y usuarios manualmente")
    print("   2. Ejecutar: python manage.py runserver")
    print("\n🔑 Credenciales de acceso:")
    print("   - Usuario: admin")
    print("   - Contraseña: admin123")
    print("   - URL: http://127.0.0.1:8000/accounts/login/")

if __name__ == "__main__":
    main()