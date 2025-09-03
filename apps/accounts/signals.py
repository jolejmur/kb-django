"""
Signals para asignación automática de roles basada en posiciones jerárquicas
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.apps import apps
from .models import Role


# Mapeo de modelos a roles
ROLE_MAPPING = {
    'Vendedor': 'Ventas',
    'TeamLeader': 'Team Leader', 
    'JefeVenta': 'Gerente de Equipo',  # Actualizado: Jefe de Venta -> Gerente de Equipo
    'GerenteEquipo': 'Gerente de Equipo',  # Gerente de Equipo
    'GerenteProyecto': 'Gerente de Proyecto',
    'JefeProyecto': 'Gerente de Equipo',  # Actualizado: Jefe de Proyecto -> Gerente de Equipo
}


def get_user_highest_role(user):
    """
    Determina el rol más alto que debería tener un usuario basado en sus posiciones
    Jerarquía (de mayor a menor):
    1. GerenteProyecto / GerenteEquipo
    2. JefeProyecto / JefeVenta  
    3. TeamLeader
    4. Vendedor
    """
    # Verificar GerenteProyecto
    if hasattr(user, 'gerente_proyectos') and user.gerente_proyectos.filter(activo=True).exists():
        return 'Gerente de Proyecto'
    
    # Verificar GerenteEquipo
    if hasattr(user, 'gerente_equipos') and user.gerente_equipos.filter(activo=True).exists():
        return 'Gerente de Equipo'
    
    # Verificar JefeProyecto 
    if hasattr(user, 'jefe_proyectos') and user.jefe_proyectos.filter(activo=True).exists():
        return 'Gerente de Equipo'
    
    # Verificar JefeVenta
    if hasattr(user, 'jefe_ventas') and user.jefe_ventas.filter(activo=True).exists():
        return 'Gerente de Equipo'
    
    # Verificar TeamLeader
    if hasattr(user, 'team_leaders') and user.team_leaders.filter(activo=True).exists():
        return 'Team Leader'
    
    # Verificar Vendedor
    if hasattr(user, 'vendedores') and user.vendedores.filter(activo=True).exists():
        return 'Ventas'
    
    # Si no tiene ninguna posición, mantener rol actual o asignar None
    return None


def get_user_highest_role_new_system(user):
    """
    Determina el rol más alto basado en el nuevo sistema de TeamMembership
    """
    try:
        # Importar aquí para evitar circular imports
        from apps.sales_team_management.models import TeamMembership
        
        # Obtener la membresía activa con el nivel jerárquico más bajo (más alto en la jerarquía)
        highest_membership = TeamMembership.objects.filter(
            user=user,
            is_active=True,
            status='ACTIVE'
        ).select_related('position_type').order_by('position_type__hierarchy_level').first()
        
        if highest_membership:
            # Mapear nivel jerárquico a rol
            level = highest_membership.position_type.hierarchy_level
            if level == 1:  # Gerente
                return 'Gerente de Equipo'
            elif level == 2:  # Jefe
                return 'Gerente de Equipo'
            elif level == 3:  # Team Leader
                return 'Team Leader'
            elif level == 4:  # Vendedor
                return 'Ventas'
        
        return None
        
    except Exception as e:
        print(f"⚠️  Error determinando rol para {user.username}: {e}")
        return None


def update_user_role_new_system(user):
    """
    Actualiza el rol del usuario basado en el nuevo sistema de TeamMembership
    """
    # Preservar roles del sistema (Super Admin, etc.)
    if user.role and user.role.is_system:
        print(f"🛡️  Usuario {user.username} mantiene rol del sistema: {user.role.name}")
        return
    
    # Preservar superusuarios
    if user.is_superuser and user.role and user.role.name == 'Super Admin':
        print(f"🔧 Usuario {user.username} mantiene rol Super Admin (superusuario)")
        return
    
    highest_role_name = get_user_highest_role_new_system(user)
    
    if highest_role_name:
        try:
            new_role = Role.objects.get(name=highest_role_name, is_active=True)
            if user.role != new_role:
                old_role = user.role.name if user.role else 'Sin rol'
                user.role = new_role
                user.save()
                print(f"👤 Usuario {user.username}: {old_role} → {new_role.name}")
        except Role.DoesNotExist:
            print(f"⚠️  Rol '{highest_role_name}' no encontrado para usuario {user.username}")
    elif not user.role or not user.role.is_system:
        # Solo quitar rol si no es un rol del sistema
        if user.role:
            old_role = user.role.name
            user.role = None
            user.save()
            print(f"👤 Usuario {user.username}: {old_role} → Sin rol")


def update_user_role(user):
    """FUNCIÓN LEGACY - usar update_user_role_new_system"""
    return update_user_role_new_system(user)


# SIGNALS LEGACY DESHABILITADOS - MODELOS ELIMINADOS
# Los modelos legacy fueron eliminados en migración 0008

# Signals para nuevo modelo de Sales Team Management
@receiver(post_save, sender='sales_team_management.TeamMembership')
def team_membership_created_or_updated(sender, instance, created, **kwargs):
    """Signal cuando se crea o actualiza una TeamMembership"""
    if instance.is_active:
        update_user_role_new_system(instance.user)


@receiver(post_delete, sender='sales_team_management.TeamMembership')
def team_membership_deleted(sender, instance, **kwargs):
    """Signal cuando se elimina una TeamMembership"""
    update_user_role_new_system(instance.user)


# Signals para modelos de Real Estate Projects
@receiver(post_save, sender='real_estate_projects.GerenteProyecto')
def gerente_proyecto_created_or_updated(sender, instance, created, **kwargs):
    """Signal cuando se crea o actualiza un GerenteProyecto"""
    update_user_role(instance.usuario)


@receiver(post_save, sender='real_estate_projects.JefeProyecto')
def jefe_proyecto_created_or_updated(sender, instance, created, **kwargs):
    """Signal cuando se crea o actualiza un JefeProyecto"""
    update_user_role(instance.usuario)


# SIGNALS LEGACY ELIMINADOS - Ver nuevos signals arriba


@receiver(post_delete, sender='real_estate_projects.GerenteProyecto')
def gerente_proyecto_deleted(sender, instance, **kwargs):
    """Signal cuando se elimina un GerenteProyecto"""
    update_user_role(instance.usuario)


@receiver(post_delete, sender='real_estate_projects.JefeProyecto')  
def jefe_proyecto_deleted(sender, instance, **kwargs):
    """Signal cuando se elimina un JefeProyecto"""
    update_user_role(instance.usuario)