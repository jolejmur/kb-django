# apps/sales_team_management/management/commands/setup_team_hierarchy_module.py

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import Role

class Command(BaseCommand):
    help = 'Configura el nuevo módulo "Jerarquía de Equipo" (vista singular)'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Configurando módulo "Jerarquía de Equipo"...')
        
        # 1. Crear el grupo/módulo "Jerarquía de Equipo" (singular)
        team_hierarchy_group, created = Group.objects.get_or_create(
            name='Jerarquía de Equipo'
        )
        
        if created:
            self.stdout.write('✅ Grupo "Jerarquía de Equipo" creado')
        else:
            self.stdout.write('ℹ️  Grupo "Jerarquía de Equipo" ya existe')
        
        # 2. Obtener permisos relevantes (mismos que "Jerarquía de Equipos" pero para vista de equipo)
        try:
            # Obtener content types relacionados con hierarchy
            from apps.sales_team_management.models import HierarchyRelation, TeamMembership
            
            hierarchy_ct = ContentType.objects.get_for_model(HierarchyRelation)
            membership_ct = ContentType.objects.get_for_model(TeamMembership)
            
            # Permisos básicos para ver la jerarquía del equipo
            view_permissions = [
                Permission.objects.get(content_type=hierarchy_ct, codename='view_hierarchyrelation'),
                Permission.objects.get(content_type=membership_ct, codename='view_teammembership'),
            ]
            
            # Agregar permisos al grupo
            team_hierarchy_group.permissions.set(view_permissions)
            self.stdout.write('✅ Permisos básicos asignados al módulo "Jerarquía de Equipo"')
            
        except Permission.DoesNotExist as e:
            self.stdout.write(f'⚠️  Algunos permisos no existen: {e}')
        
        # 3. Asignar el nuevo módulo a roles existentes que ya tengan "Jerarquía de Equipos"
        roles_with_hierarchy = Role.objects.filter(groups__name='Jerarquía de Equipos').distinct()
        
        for role in roles_with_hierarchy:
            # Agregar el nuevo módulo si no lo tiene
            if not role.groups.filter(name='Jerarquía de Equipo').exists():
                role.groups.add(team_hierarchy_group)
                self.stdout.write(f'✅ Módulo "Jerarquía de Equipo" agregado al rol: {role.name}')
        
        # 4. Crear una versión específica para gerentes de equipo si no existe
        manager_group, created = Group.objects.get_or_create(
            name='Jerarquía de Equipo - Gerente'
        )
        
        if created:
            self.stdout.write('✅ Grupo "Jerarquía de Equipo - Gerente" creado')
            
            # Agregar permisos de creación de relaciones jerárquicas para gerentes
            try:
                create_permissions = [
                    Permission.objects.get(content_type=hierarchy_ct, codename='add_hierarchyrelation'),
                    Permission.objects.get(content_type=hierarchy_ct, codename='change_hierarchyrelation'),
                ]
                
                # Gerentes tienen permisos de vista + creación
                all_permissions = view_permissions + create_permissions
                manager_group.permissions.set(all_permissions)
                
                self.stdout.write('✅ Permisos extendidos asignados para gerentes')
                
            except Permission.DoesNotExist as e:
                self.stdout.write(f'⚠️  Algunos permisos para gerentes no existen: {e}')
        
        # 5. Crear el elemento de navegación para el sidebar
        try:
            from apps.accounts.models import Navigation, MenuCategory
            
            # Obtener la categoría "EQUIPOS DE VENTA"
            equipos_category = MenuCategory.objects.get(name='EQUIPOS DE VENTA')
            
            # Eliminar el elemento de navegación obsoleto "Jerarquía de Equipo" (singular)
            obsolete_nav = Navigation.objects.filter(
                name='Jerarquía de Equipo',
                url='/sales/team-hierarchy/'
            )
            if obsolete_nav.exists():
                obsolete_nav.delete()
                self.stdout.write('🗑️  Elemento de navegación obsoleto "Jerarquía de Equipo" eliminado')
            else:
                self.stdout.write('ℹ️  Elemento de navegación obsoleto ya estaba eliminado')
                
        except Exception as e:
            self.stdout.write(f'⚠️  Error creando elemento de navegación: {e}')
        
        # 6. Resumen final
        self.stdout.write('\n' + '='*60)
        self.stdout.write('📋 RESUMEN DE CONFIGURACIÓN:')
        self.stdout.write('='*60)
        self.stdout.write(f'✅ Módulo "Jerarquía de Equipo" configurado')
        self.stdout.write(f'✅ Módulo "Jerarquía de Equipo - Gerente" configurado')
        self.stdout.write(f'✅ {roles_with_hierarchy.count()} roles actualizados')
        self.stdout.write('\n📍 RUTAS DISPONIBLES:')
        self.stdout.write('   • Vista unificada: /sales/hierarchy/ (con control de acceso automático)')
        self.stdout.write('   • Vista plural: /sales/hierarchy/ (todos los equipos)')
        self.stdout.write('\n💡 Los usuarios ahora verán ambos módulos en el sidebar')
        self.stdout.write('='*60)