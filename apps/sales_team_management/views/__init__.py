# apps/sales_team_management/views/__init__.py

# Import all views from their respective modules to maintain compatibility with urls.py
from .dashboard import sales_dashboard
from .equipos import (
    equipos_list,
    equipo_detail,
    crear_equipo,
    agregar_miembro,
    editar_miembro,
    remover_miembro,
    get_team_members_json,
    get_available_positions,
)
from .jerarquia import (
    jerarquia_list,
    jerarquia_detail,
    jerarquia_toggle,
    jerarquia_equipo,
    crear_relacion_jerarquica,
    crear_relacion_jerarquica_equipo,
    editar_relacion_jerarquica,
    eliminar_relacion_jerarquica,
    analisis_jerarquia,
    get_hierarchy_json,
    get_available_supervisors,
    asignar_supervisor,
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
    comisiones_equipo_config,
    comisiones_desarrollo_config,
    comision_structure_detail,
    get_commission_structure_json,
)
from .ajax_views import (
    ajax_equipos_search,
    ajax_proyectos_search,
    ajax_inmuebles_by_proyecto,
    ajax_search_users,
    ajax_create_user,
    ajax_search_hierarchy,
    ajax_toggle_public_registration,
    ajax_generate_username,
)
from .supervision_directa import (
    supervision_directa_list,
    supervision_directa_create,
    supervision_directa_edit,
    supervision_directa_detail,
    supervision_directa_toggle,
    supervision_directa_delete,
    ajax_supervisores_disponibles,
    ajax_subordinados_disponibles,
    ajax_validar_supervision_relation,
)
from .permission_views import (
    permission_denied_view,
)
from .public_registration import (
    public_register_form,
    public_register_submit,
    public_register_success,
)

__all__ = [
    # Dashboard
    'sales_dashboard',
    
    # Equipos
    'equipos_list',
    'equipo_detail',
    'crear_equipo',
    'agregar_miembro',
    'editar_miembro',
    'remover_miembro',
    'get_team_members_json',
    'get_available_positions',
    
    # Jerarquía
    'jerarquia_list',
    'jerarquia_detail',
    'jerarquia_toggle',
    'jerarquia_equipo',
    'crear_relacion_jerarquica',
    'crear_relacion_jerarquica_equipo',
    'editar_relacion_jerarquica',
    'eliminar_relacion_jerarquica',
    'analisis_jerarquia',
    'get_hierarchy_json',
    'get_available_supervisors',
    'asignar_supervisor',
    
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
    'comisiones_equipo_config',
    'comisiones_desarrollo_config',
    'comision_structure_detail',
    'get_commission_structure_json',
    
    # AJAX
    'ajax_equipos_search',
    'ajax_proyectos_search',
    'ajax_inmuebles_by_proyecto',
    'ajax_search_users',
    'ajax_create_user',
    'ajax_search_hierarchy',
    'ajax_toggle_public_registration',
    'ajax_generate_username',
    
    # Supervisión Directa
    'supervision_directa_list',
    'supervision_directa_create',
    'supervision_directa_edit',
    'supervision_directa_detail',
    'supervision_directa_toggle',
    'supervision_directa_delete',
    'ajax_supervisores_disponibles',
    'ajax_subordinados_disponibles',
    'ajax_validar_supervision_relation',
    
    # Permission views
    'permission_denied_view',
    
    # Public registration views
    'public_register_form',
    'public_register_submit', 
    'public_register_success',
]