# apps/communications/utils/filters.py
from django.db.models import Q
from django.utils import timezone
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LeadFilters:
    """
    Utilidades para filtrar leads
    """
    
    @staticmethod
    def apply_date_filters(queryset, fecha_desde=None, fecha_hasta=None):
        """
        Aplica filtros de fecha
        """
        if fecha_desde:
            if isinstance(fecha_desde, str):
                fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__gte=fecha_desde)
        
        if fecha_hasta:
            if isinstance(fecha_hasta, str):
                fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
            queryset = queryset.filter(created_at__date__lte=fecha_hasta)
        
        return queryset
    
    @staticmethod
    def apply_status_filter(queryset, estado):
        """
        Aplica filtro por estado
        """
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset
    
    @staticmethod
    def apply_search_filter(queryset, search_term):
        """
        Aplica filtro de búsqueda en múltiples campos
        """
        if search_term:
            queryset = queryset.filter(
                Q(cliente__nombre_completo__icontains=search_term) |
                Q(cliente__numero_whatsapp__icontains=search_term) |
                Q(notas__icontains=search_term)
            )
        return queryset
    
    @staticmethod
    def apply_assignment_filter(queryset, assignment_status):
        """
        Aplica filtro por estado de asignación
        """
        if assignment_status == 'assigned':
            queryset = queryset.filter(assignments__assigned_to_user__isnull=False)
        elif assignment_status == 'unassigned':
            queryset = queryset.filter(assignments__assigned_to_user__isnull=True)
        
        return queryset


class ConversationFilters:
    """
    Utilidades para filtrar conversaciones
    """
    
    @staticmethod
    def apply_status_filter(queryset, estado):
        """
        Aplica filtro por estado de conversación
        """
        if estado:
            queryset = queryset.filter(estado=estado)
        return queryset
    
    @staticmethod
    def apply_unread_filter(queryset, show_unread_only=False):
        """
        Aplica filtro para mostrar solo no leídos
        """
        if show_unread_only:
            queryset = queryset.filter(mensajes_no_leidos__gt=0)
        return queryset
    
    @staticmethod
    def apply_assignment_filter(queryset, assignment_status):
        """
        Aplica filtro por estado de asignación
        """
        if assignment_status == 'assigned':
            queryset = queryset.filter(
                numero_whatsapp__in=queryset.values_list('numero_whatsapp', flat=True)
            ).extra(
                where=["""
                    EXISTS (
                        SELECT 1 FROM communications_leadassignment la
                        INNER JOIN communications_lead l ON la.lead_id = l.id
                        WHERE l.cliente_id = communications_conversacion.cliente_id
                        AND la.assigned_to_user_id IS NOT NULL
                        AND la.is_active = true
                    )
                """]
            )
        elif assignment_status == 'unassigned':
            queryset = queryset.extra(
                where=["""
                    NOT EXISTS (
                        SELECT 1 FROM communications_leadassignment la
                        INNER JOIN communications_lead l ON la.lead_id = l.id
                        WHERE l.cliente_id = communications_conversacion.cliente_id
                        AND la.assigned_to_user_id IS NOT NULL
                        AND la.is_active = true
                    )
                """]
            )
        
        return queryset


class TimeFilters:
    """
    Utilidades para filtros temporales
    """
    
    @staticmethod
    def get_time_range_filter(time_range):
        """
        Obtiene filtro de rango temporal
        """
        now = timezone.now()
        
        if time_range == 'today':
            return now.date()
        elif time_range == 'week':
            week_start = now.date() - timezone.timedelta(days=now.weekday())
            return week_start
        elif time_range == 'month':
            return now.date().replace(day=1)
        elif time_range == 'quarter':
            quarter_month = ((now.month - 1) // 3) * 3 + 1
            return now.date().replace(month=quarter_month, day=1)
        elif time_range == 'year':
            return now.date().replace(month=1, day=1)
        
        return None
    
    @staticmethod
    def apply_time_range_filter(queryset, time_range, date_field='created_at'):
        """
        Aplica filtro de rango temporal a queryset
        """
        start_date = TimeFilters.get_time_range_filter(time_range)
        if start_date:
            filter_kwargs = {f'{date_field}__date__gte': start_date}
            queryset = queryset.filter(**filter_kwargs)
        
        return queryset


class PaginationHelper:
    """
    Utilidades para paginación
    """
    
    @staticmethod
    def paginate_queryset(queryset, page=1, per_page=20):
        """
        Pagina un queryset
        """
        try:
            page = int(page)
            per_page = int(per_page)
            
            # Limitar per_page a un máximo razonable
            per_page = min(per_page, 100)
            
            start = (page - 1) * per_page
            end = start + per_page
            
            total = queryset.count()
            items = queryset[start:end]
            
            has_next = end < total
            has_previous = page > 1
            
            return {
                'items': items,
                'page': page,
                'per_page': per_page,
                'total': total,
                'has_next': has_next,
                'has_previous': has_previous,
                'total_pages': (total + per_page - 1) // per_page
            }
            
        except (ValueError, TypeError):
            # Si hay error en parámetros, usar valores por defecto
            return PaginationHelper.paginate_queryset(queryset, 1, 20)