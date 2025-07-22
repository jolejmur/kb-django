# apps/sales_team_management/views/__init__.py

# Import all views from their respective modules to maintain compatibility with urls.py
from .dashboard import sales_dashboard
from .helpers import get_member_by_role
from .equipos import (
    equipos_venta_list,
    equipos_venta_detail,
    equipos_venta_create,
    equipos_venta_edit,
    equipos_venta_delete,
    equipos_manage_hierarchy,
    equipos_add_gerente,
    equipos_add_member,
)
from .jerarquia import (
    jerarquia_equipos_list,
    jerarquia_create_member,
    jerarquia_member_detail,
    jerarquia_member_edit,
    jerarquia_member_delete,
    jerarquia_member_reassign,
    jerarquia_member_deactivate,
    jerarquia_member_toggle_status,
)
from .proyectos import (
    proyectos_list,
    proyectos_detail,
    proyectos_create,
    proyectos_edit,
    proyectos_delete,
)
from .inmuebles import (
    inmuebles_list,
    inmuebles_detail,
    inmuebles_create,
    inmuebles_edit,
    inmuebles_delete,
)
from .comisiones import (
    comisiones_equipos_list,
    comisiones_proyectos_list,
    comisiones_venta_config,
    comisiones_desarrollo_config,
)
from .ajax_views import (
    ajax_equipos_search,
    ajax_proyectos_search,
    ajax_inmuebles_by_proyecto,
    ajax_cambiar_estado_miembro,
    ajax_migrar_miembro,
    ajax_verificar_subordinados,
    ajax_get_supervisores,
    ajax_search_users,
    ajax_create_user,
)

__all__ = [
    # Dashboard
    'sales_dashboard',
    
    # Helpers
    'get_member_by_role',
    
    # Equipos
    'equipos_venta_list',
    'equipos_venta_detail',
    'equipos_venta_create',
    'equipos_venta_edit',
    'equipos_venta_delete',
    'equipos_manage_hierarchy',
    'equipos_add_gerente',
    'equipos_add_member',
    
    # Jerarquía
    'jerarquia_equipos_list',
    'jerarquia_create_member',
    'jerarquia_member_detail',
    'jerarquia_member_edit',
    'jerarquia_member_delete',
    'jerarquia_member_reassign',
    'jerarquia_member_deactivate',
    'jerarquia_member_toggle_status',
    
    # Proyectos
    'proyectos_list',
    'proyectos_detail',
    'proyectos_create',
    'proyectos_edit',
    'proyectos_delete',
    
    # Inmuebles
    'inmuebles_list',
    'inmuebles_detail',
    'inmuebles_create',
    'inmuebles_edit',
    'inmuebles_delete',
    
    # Comisiones
    'comisiones_equipos_list',
    'comisiones_proyectos_list',
    'comisiones_venta_config',
    'comisiones_desarrollo_config',
    
    # AJAX
    'ajax_equipos_search',
    'ajax_proyectos_search',
    'ajax_inmuebles_by_proyecto',
    'ajax_cambiar_estado_miembro',
    'ajax_migrar_miembro',
    'ajax_verificar_subordinados',
    'ajax_get_supervisores',
    'ajax_search_users',
    'ajax_create_user',
]