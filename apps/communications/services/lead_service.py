# apps/communications/services/lead_service.py
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ..models import Lead, LeadAssignment, LeadDistributionConfig
from apps.sales_team_management.models import TeamMembership, OrganizationalUnit
import logging

logger = logging.getLogger(__name__)


class LeadService:
    """
    Servicio para manejar la lógica de negocio de leads
    """
    
    @staticmethod
    def get_user_team_info(user):
        """
        Obtiene información del equipo del usuario
        """
        user_membership = TeamMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related('organizational_unit', 'position_type').first()
        
        user_team = None
        is_team_member = False
        can_change_filter = True
        forced_filter = None
        
        if user_membership:
            user_team = user_membership.organizational_unit
            is_team_member = True
            can_change_filter = False
            forced_filter = str(user_team.id)
        
        return {
            'user_team': user_team,
            'is_team_member': is_team_member,
            'can_change_filter': can_change_filter,
            'forced_filter': forced_filter,
            'membership': user_membership
        }
    
    @staticmethod
    def validate_team_filter_security(user, requested_filter):
        """
        Valida filtros de seguridad para equipos
        """
        team_info = LeadService.get_user_team_info(user)
        
        if team_info['is_team_member'] and team_info['forced_filter']:
            if requested_filter and requested_filter != team_info['forced_filter']:
                return False, team_info['forced_filter']
        
        return True, requested_filter or team_info['forced_filter']
    
    @staticmethod
    def get_leads_stats(user, sales_unit_filter=None):
        """
        Obtiene estadísticas de leads para un usuario
        """
        team_info = LeadService.get_user_team_info(user)
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Query base
        leads_base_query = Lead.objects.filter(is_active=True)
        assignments_base_query = LeadAssignment.objects.filter(is_active=True)
        
        # Aplicar filtro de equipo si es necesario
        if team_info['is_team_member'] and team_info['user_team']:
            leads_base_query = leads_base_query.filter(
                assignments__organizational_unit=team_info['user_team'],
                assignments__is_active=True
            ).distinct()
            assignments_base_query = assignments_base_query.filter(
                organizational_unit=team_info['user_team']
            )
        elif sales_unit_filter:
            # Filtro opcional para usuarios sin restricciones
            try:
                unit = OrganizationalUnit.objects.get(id=sales_unit_filter)
                leads_base_query = leads_base_query.filter(
                    assignments__organizational_unit=unit,
                    assignments__is_active=True
                ).distinct()
                assignments_base_query = assignments_base_query.filter(
                    organizational_unit=unit
                )
            except OrganizationalUnit.DoesNotExist:
                pass
        
        # Contadores por estado
        stats = {
            'total_leads': leads_base_query.count(),
            'nuevos': leads_base_query.filter(estado='nuevo').count(),
            'contactados': leads_base_query.filter(estado='contactado').count(),
            'calificados': leads_base_query.filter(estado='calificado').count(),
            'perdidos': leads_base_query.filter(estado='perdido').count(),
            'asignados': assignments_base_query.filter(assigned_to_user__isnull=False).count(),
            'no_asignados': assignments_base_query.filter(assigned_to_user__isnull=True).count(),
        }
        
        # Estadísticas temporales
        stats.update({
            'leads_hoy': leads_base_query.filter(created_at__date=today).count(),
            'leads_semana': leads_base_query.filter(created_at__date__gte=week_start).count(),
            'leads_mes': leads_base_query.filter(created_at__date__gte=month_start).count(),
        })
        
        return stats
    
    @staticmethod
    def get_all_distribution_configs():
        """
        Obtiene configuraciones de distribución para todos los equipos
        """
        from django.utils import timezone
        from datetime import timedelta
        
        # Obtener todas las configuraciones activas
        configs = LeadDistributionConfig.objects.filter(
            organizational_unit__unit_type='SALES',
            organizational_unit__is_active=True
        ).select_related('organizational_unit').order_by('organizational_unit__name')
        
        configs_data = []
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        for config in configs:
            # Estadísticas para este equipo
            team_assignments = LeadAssignment.objects.filter(
                organizational_unit=config.organizational_unit,
                is_active=True
            )
            
            leads_today = team_assignments.filter(assigned_date__date=today).count()
            leads_week = team_assignments.filter(assigned_date__date__gte=week_start).count()
            team_members = TeamMembership.objects.filter(
                organizational_unit=config.organizational_unit,
                is_active=True
            ).count()
            
            # Agregar estadísticas al config
            config.stats = {
                'leads_today': leads_today,
                'leads_this_week': leads_week,
                'team_members_count': team_members,
                'can_receive_more': True  # Placeholder - implementar lógica si es necesario
            }
            
            configs_data.append(config)
        
        return configs_data
    
    @staticmethod
    def get_distribution_stats():
        """
        Obtiene estadísticas generales de distribución
        """
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        # Configuraciones activas
        active_configs = LeadDistributionConfig.objects.filter(
            is_active_for_leads=True,
            organizational_unit__unit_type='SALES',
            organizational_unit__is_active=True
        ).count()
        
        # Leads hoy y esta semana
        leads_today = LeadAssignment.objects.filter(
            is_active=True,
            assigned_date__date=today
        ).count()
        
        leads_week = LeadAssignment.objects.filter(
            is_active=True,
            assigned_date__date__gte=week_start
        ).count()
        
        return {
            'total_active_configs': active_configs,
            'total_leads_today': leads_today,
            'total_leads_this_week': leads_week
        }
    
    @staticmethod
    def get_filtered_leads(user, filters=None):
        """
        Obtiene leads filtrados según permisos de usuario
        """
        team_info = LeadService.get_user_team_info(user)
        filters = filters or {}
        
        # Query base
        queryset = Lead.objects.filter(is_active=True)
        
        # Aplicar filtro de acceso jerárquico
        if team_info['is_team_member'] and team_info['user_team']:
            # Usuario con equipo - obtener leads accesibles según jerarquía
            accessible_leads = LeadService.get_accessible_leads_for_management(user)
            lead_ids = [lead.id for lead in accessible_leads]
            queryset = queryset.filter(id__in=lead_ids).distinct()
        # Si no tiene equipo específico - puede ver TODOS los leads (sin filtro)
        
        # Aplicar filtros adicionales
        if filters.get('estado'):
            queryset = queryset.filter(estado=filters['estado'])
        
        if filters.get('fecha_desde'):
            queryset = queryset.filter(created_at__date__gte=filters['fecha_desde'])
        
        if filters.get('fecha_hasta'):
            queryset = queryset.filter(created_at__date__lte=filters['fecha_hasta'])
        
        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(cliente__nombre_completo__icontains=search_term) |
                Q(cliente__numero_whatsapp__icontains=search_term) |
                Q(notas__icontains=search_term)
            )
        
        return queryset.select_related('cliente').prefetch_related('assignments')
    
    @staticmethod
    def get_accessible_leads_for_management(user):
        """
        Obtiene leads accesibles para gestión según jerarquía del usuario
        """
        import logging
        logger = logging.getLogger(__name__)
        
        from apps.sales_team_management.models import HierarchyRelation
        
        logger.info(f"🔍 DEBUG get_accessible_leads_for_management: user={user.username}")
        
        # Verificar si el usuario tiene equipo
        user_membership = TeamMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related('organizational_unit', 'position_type').first()
        
        logger.info(f"🔍 DEBUG user_membership: {user_membership}")
        if user_membership:
            logger.info(f"🔍 DEBUG unit: {user_membership.organizational_unit.name} (type: {user_membership.organizational_unit.unit_type})")
        
        if not user_membership:
            # Usuario sin equipo (admin, gerente comercial) - TODOS los leads
            logger.info("🔍 DEBUG: Usuario sin equipo - devolviendo todos los leads")
            return Lead.objects.filter(is_active=True).select_related('cliente')
        
        # Para equipos de venta (SALES), todos los miembros pueden ver todos los leads del equipo
        # independientemente de la jerarquía
        if user_membership.organizational_unit.unit_type == 'SALES':
            logger.info(f"🔍 DEBUG: Usuario de equipo SALES - buscando leads del equipo {user_membership.organizational_unit.name}")
            # Obtener TODOS los leads asignados al equipo (sin importar jerarquía)
            team_assignments = LeadAssignment.objects.filter(
                organizational_unit=user_membership.organizational_unit,
                is_active=True
            ).select_related('lead__cliente')
            
            logger.info(f"🔍 DEBUG: Encontradas {team_assignments.count()} asignaciones para el equipo")
            
            leads = [assignment.lead for assignment in team_assignments]
            logger.info(f"🔍 DEBUG: Devolviendo {len(leads)} leads del equipo")
            return leads
        
        # Para otros tipos de equipos, mantener la lógica jerárquica original
        # Si es gerente de equipo, puede ver todos los leads de su equipo
        if user_membership.position_type and 'gerente' in user_membership.position_type.name.lower():
            # Gerente puede ver todos los leads asignados a su equipo
            team_assignments = LeadAssignment.objects.filter(
                organizational_unit=user_membership.organizational_unit,
                is_active=True
            ).select_related('lead__cliente')
            
            return [assignment.lead for assignment in team_assignments]
        
        # Usuario con equipo (no de ventas) - obtener leads de subalternos (lógica original)
        subordinate_users = set()
        
        # 1. Supervisión directa
        direct_subordinates = HierarchyRelation.objects.filter(
            supervisor_membership__user=user,
            is_active=True,
            relation_type='DIRECT_SUPERVISION'
        ).values_list('subordinate_membership__user', flat=True)
        subordinate_users.update(direct_subordinates)
        
        # 2. Supervisión rígida (jerárquica)
        hierarchical_subordinates = HierarchyRelation.objects.filter(
            supervisor_membership__user=user,
            is_active=True,
            relation_type='HIERARCHICAL'
        ).values_list('subordinate_membership__user', flat=True)
        subordinate_users.update(hierarchical_subordinates)
        
        # 3. Incluir al propio usuario (puede ver sus propios leads también)
        subordinate_users.add(user.id)
        
        # Si no tiene subalternos configurados pero está en un equipo, incluir todo el equipo
        if not subordinate_users or len(subordinate_users) == 1:  # Solo tiene su propio usuario
            team_members = TeamMembership.objects.filter(
                organizational_unit=user_membership.organizational_unit,
                is_active=True
            ).values_list('user', flat=True)
            subordinate_users.update(team_members)
        
        # Obtener leads asignados a todos los subalternos
        subordinate_assignments = LeadAssignment.objects.filter(
            assigned_to_user_id__in=subordinate_users,
            is_active=True
        ).select_related('lead__cliente')
        
        return [assignment.lead for assignment in subordinate_assignments]
    
    @staticmethod
    def assign_lead_to_user(lead_id, assigned_to_user_id, assigned_by_user):
        """
        Asigna un lead a un usuario específico
        """
        try:
            lead = get_object_or_404(Lead, id=lead_id, is_active=True)
            
            # Buscar usuario a asignar
            from apps.accounts.models import User
            assigned_user = get_object_or_404(User, id=assigned_to_user_id)
            
            # Buscar el equipo del usuario asignado
            user_membership = TeamMembership.objects.filter(
                user=assigned_user,
                is_active=True,
                status='ACTIVE'
            ).first()
            
            if not user_membership:
                return False, "El usuario no pertenece a ningún equipo activo"
            
            # Buscar asignación existente
            assignment = LeadAssignment.objects.filter(
                lead=lead,
                is_active=True
            ).first()
            
            if assignment:
                # Verificar si el usuario pertenece al mismo equipo de la asignación existente
                if assignment.organizational_unit != user_membership.organizational_unit:
                    # Cambiar asignación a otro equipo
                    assignment.organizational_unit = user_membership.organizational_unit
            else:
                # Crear nueva asignación
                assignment = LeadAssignment.objects.create(
                    lead=lead,
                    organizational_unit=user_membership.organizational_unit,
                    assigned_by=assigned_by_user,
                    assignment_type='MANUAL',
                    is_active=True
                )
            
            # Asignar usuario
            assignment.assigned_to_user = assigned_user
            assignment.assigned_by = assigned_by_user
            assignment.assigned_date = timezone.now()
            assignment.save()
            
            # Actualizar estado del lead
            lead.estado = 'asignado'
            lead.save()
            
            return True, "Lead asignado correctamente"
            
        except Exception as e:
            logger.error(f'Error asignando lead {lead_id}: {str(e)}')
            return False, str(e)
    
    @staticmethod
    def reject_lead(lead_id, user, reason=None):
        """
        Rechaza un lead
        """
        try:
            lead = get_object_or_404(Lead, id=lead_id, is_active=True)
            
            # Verificar que el usuario tiene acceso al lead
            assignment = LeadAssignment.objects.filter(
                lead=lead,
                assigned_to_user=user,
                is_active=True
            ).first()
            
            if not assignment:
                return False, "No tienes asignado este lead"
            
            # Actualizar lead
            lead.estado = 'perdido'
            if reason:
                lead.notas = f"{lead.notas or ''}\n\nRechazado por {user.get_full_name()}: {reason}".strip()
            lead.save()
            
            # Desactivar asignación
            assignment.is_active = False
            assignment.save()
            
            return True, "Lead rechazado correctamente"
            
        except Exception as e:
            logger.error(f'Error rechazando lead {lead_id}: {str(e)}')
            return False, str(e)
    
    @staticmethod
    def get_distribution_config():
        """
        Obtiene la configuración de distribución de leads
        """
        try:
            config = LeadDistributionConfig.objects.first()
            if not config:
                # Crear configuración por defecto
                config = LeadDistributionConfig.objects.create(
                    is_active=True,
                    distribution_method='round_robin',
                    auto_assign=True
                )
            return config
        except Exception as e:
            logger.error(f'Error obteniendo configuración de distribución: {str(e)}')
            return None