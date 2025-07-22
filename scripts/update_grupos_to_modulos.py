#!/usr/bin/env python
"""
Script para actualizar "Grupos de Trabajo" a "Módulos" en la base de datos
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.accounts.models import Navigation
from django.contrib.auth.models import Group

def update_grupos_to_modulos():
    """Actualizar 'Grupos de Trabajo' a 'Módulos'"""
    print("🔄 Actualizando 'Grupos de Trabajo' a 'Módulos'...")
    
    try:
        # Buscar el grupo "Grupos de Trabajo"
        group = Group.objects.get(name='Grupos de Trabajo')
        
        # Cambiar el nombre del grupo
        group.name = 'Módulos'
        group.save()
        
        # Actualizar la navegación asociada
        try:
            navigation = Navigation.objects.get(group=group)
            navigation.name = 'Módulos'
            navigation.icon = 'fas fa-cubes'
            navigation.save()
            
            print("✅ Actualización completada:")
            print(f"   • Grupo: {group.name}")
            print(f"   • Navegación: {navigation.name}")
            print(f"   • Ícono: {navigation.icon}")
            
        except Navigation.DoesNotExist:
            print("⚠️  Navegación para 'Módulos' no encontrada")
            
    except Group.DoesNotExist:
        print("⚠️  Grupo 'Grupos de Trabajo' no encontrado")
        print("💡 Ejecutando script completo para crear la estructura...")
        
        # Ejecutar el script completo
        from scripts.setup_roles_permissions import main as setup_main
        setup_main()

if __name__ == "__main__":
    update_grupos_to_modulos()