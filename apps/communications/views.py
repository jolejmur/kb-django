# apps/communications/views.py
# Archivo de compatibilidad - importa todas las vistas desde los módulos especializados

# Importar todas las vistas desde los módulos especializados para mantener compatibilidad
from .views.chat_views import (
    supervision_chat,
    chat_vendedor,
    get_conversations,
    get_vendedor_conversations,
    get_conversation_messages,
    get_vendedor_conversation_messages
)

from .views.lead_management import (
    lead_management_dashboard,
    leads_list,
    lead_distribution_config,
    lead_assignments_history
)

from .views.api_endpoints import (
    send_message,
    send_vendedor_message,
    send_vendedor_media,
    update_lead_distribution,
    assign_lead_to_salesperson,
    get_sales_team_members,
    reject_lead,
    manual_lead_assignment
)

from .views.webhook_handlers import (
    webhook_whatsapp,
    status_api,
    send_test_message,
    get_debug_messages,
    test_webhook
)

from .views.supervision import (
    supervision_dashboard,
    get_supervision_conversations,
    get_supervision_conversation_messages,
    send_supervision_message,
    send_supervision_media,
    get_team_performance,
    get_conversation_analytics
)

from .views.config_media import (
    configuracion_whatsapp,
    activar_configuracion,
    eliminar_configuracion,
    serve_audio_converted,
    test_audio_debug,
    media_upload_test,
    cleanup_temp_files
)

# Importar funciones de utilidad para mantener compatibilidad
from .utils.permissions import (
    check_whatsapp_access,
    check_chat_supervision_access,
    check_chat_vendedor_access,
    check_lead_management_access
)

# Re-exportar para compatibilidad con imports existentes
__all__ = [
    # Chat views
    'supervision_chat',
    'chat_vendedor',
    'get_conversations',
    'get_vendedor_conversations',
    'get_conversation_messages',
    'get_vendedor_conversation_messages',
    
    # Lead management
    'lead_management_dashboard',
    'leads_list',
    'lead_distribution_config',
    'lead_assignments_history',
    
    # API endpoints
    'send_message',
    'send_vendedor_message',
    'send_vendedor_media',
    'update_lead_distribution',
    'assign_lead_to_salesperson',
    'get_sales_team_members',
    'reject_lead',
    'manual_lead_assignment',
    
    # Webhook handlers
    'webhook_whatsapp',
    'status_api',
    'send_test_message',
    'get_debug_messages',
    'test_webhook',
    
    # Supervision
    'supervision_dashboard',
    'get_supervision_conversations',
    'get_supervision_conversation_messages',
    'send_supervision_message',
    'send_supervision_media',
    'get_team_performance',
    'get_conversation_analytics',
    
    # Config and media
    'configuracion_whatsapp',
    'activar_configuracion',
    'eliminar_configuracion',
    'serve_audio_converted',
    'test_audio_debug',
    'media_upload_test',
    'cleanup_temp_files',
    
    # Utility functions
    'check_whatsapp_access',
    'check_chat_supervision_access',
    'check_chat_vendedor_access',
    'check_lead_management_access',
]