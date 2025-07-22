# apps/sales_team_management/views/helpers.py

from ..models import GerenteEquipo, JefeVenta, TeamLeader, Vendedor


def get_member_by_role(member_id, rol):
    """
    Función helper para obtener un miembro según su rol
    Retorna: (miembro_actual, usuario, equipo_actual)
    """
    from django.contrib.auth.models import User
    
    try:
        if rol == 'gerente':
            miembro_actual = GerenteEquipo.objects.get(id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.equipo_venta
        elif rol == 'jefe':
            miembro_actual = JefeVenta.objects.get(id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.gerente_equipo.equipo_venta
        elif rol == 'team_leader':
            miembro_actual = TeamLeader.objects.get(id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.jefe_venta.gerente_equipo.equipo_venta
        elif rol == 'vendedor':
            miembro_actual = Vendedor.objects.get(id=member_id)
            usuario = miembro_actual.usuario
            equipo_actual = miembro_actual.team_leader.jefe_venta.gerente_equipo.equipo_venta
        else:
            return None, None, None
        
        return miembro_actual, usuario, equipo_actual
        
    except (GerenteEquipo.DoesNotExist, JefeVenta.DoesNotExist, 
            TeamLeader.DoesNotExist, Vendedor.DoesNotExist):
        return None, None, None