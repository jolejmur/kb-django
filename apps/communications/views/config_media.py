# apps/communications/views/config_media.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, FileResponse, Http404
from django.core.files.storage import default_storage
from django.conf import settings
from ..models import WhatsAppConfig, Mensaje
from ..forms import WhatsAppConfigForm
from ..services.message_service import MessageService
from ..utils.permissions import require_whatsapp_access, api_require_whatsapp_access
from ..utils.formatters import ResponseFormatter
import os
import logging

logger = logging.getLogger(__name__)


@login_required
@require_whatsapp_access
def configuracion_whatsapp(request):
    """
    Vista para configurar WhatsApp Business
    """
    # Obtener la configuración actual (solo puede haber una activa)
    config = WhatsAppConfig.objects.filter(is_active=True).first()
    configs = WhatsAppConfig.objects.all().order_by('-created_at')
    
    if request.method == 'POST':
        form = WhatsAppConfigForm(request.POST)
        if form.is_valid():
            try:
                # Desactivar configuraciones existentes
                WhatsAppConfig.objects.filter(is_active=True).update(is_active=False)
                
                # Crear nueva configuración
                new_config = form.save(commit=False)
                new_config.created_by = request.user
                new_config.is_active = True
                new_config.save()
                
                messages.success(request, 'Configuración de WhatsApp guardada exitosamente')
                return redirect('communications:configuracion')
                
            except Exception as e:
                logger.error(f'Error guardando configuración: {str(e)}')
                messages.error(request, f'Error al guardar la configuración: {str(e)}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario')
    else:
        form = WhatsAppConfigForm()
    
    # Obtener mensajes de debug recientes para mostrar en el template
    debug_messages = []
    if config:
        from ..models import WebhookDebugMessage
        debug_messages = WebhookDebugMessage.objects.filter(
            config_utilizada=config
        ).order_by('-created_at')[:10]

    context = {
        'form': form,
        'config': config,  # Variable original que espera el template
        'configs': configs,
        'active_config': config,
        'has_active_config': config is not None,  # Variable que faltaba
        'debug_messages': debug_messages,  # Variable que faltaba
        'page_title': 'Configuración WhatsApp Business',
        'breadcrumbs': [
            {'name': 'Gestión de Leads', 'url': None},
            {'name': 'Configuración WhatsApp', 'url': None}
        ],
    }
    
    return render(request, 'communications/config/configuracion.html', context)


@login_required
@require_http_methods(["POST"])
@require_whatsapp_access
def activar_configuracion(request, config_id):
    """
    Activa una configuración específica de WhatsApp
    """
    try:
        config = get_object_or_404(WhatsAppConfig, id=config_id)
        
        # Desactivar todas las configuraciones
        WhatsAppConfig.objects.filter(is_active=True).update(is_active=False)
        
        # Activar la seleccionada
        config.is_active = True
        config.save()
        
        messages.success(request, f'Configuración ID {config.id} activada exitosamente')
        
    except Exception as e:
        logger.error(f'Error activando configuración {config_id}: {str(e)}')
        messages.error(request, f'Error al activar la configuración: {str(e)}')
    
    return redirect('communications:configuracion')


@login_required
@require_http_methods(["POST"])
@require_whatsapp_access
def eliminar_configuracion(request, config_id):
    """
    Elimina una configuración de WhatsApp
    """
    try:
        config = get_object_or_404(WhatsAppConfig, id=config_id)
        
        if config.is_active:
            messages.error(request, 'No se puede eliminar la configuración activa')
        else:
            config_id_to_delete = config.id
            config.delete()
            messages.success(request, f'Configuración ID {config_id_to_delete} eliminada exitosamente')
        
    except Exception as e:
        logger.error(f'Error eliminando configuración {config_id}: {str(e)}')
        messages.error(request, f'Error al eliminar la configuración: {str(e)}')
    
    return redirect('communications:configuracion')


def serve_audio_converted(request, message_id):
    """
    Sirve archivos de audio convertidos a OGG para reproducción web
    """
    try:
        mensaje = get_object_or_404(Mensaje, id=message_id)
        
        # Verificar que es un mensaje de audio
        if mensaje.tipo != 'audio' or not mensaje.archivo_local:
            raise Http404("Archivo de audio no encontrado")
        
        # Intentar conversión a OGG si es necesario
        success, result = MessageService.convert_audio_to_ogg(message_id)
        
        if not success:
            logger.error(f'Error convirtiendo audio {message_id}: {result}')
            raise Http404("Error procesando archivo de audio")
        
        # Servir archivo convertido
        ogg_path = result
        if os.path.exists(ogg_path):
            return FileResponse(
                open(ogg_path, 'rb'),
                content_type='audio/ogg',
                filename=f'audio_{message_id}.ogg'
            )
        else:
            raise Http404("Archivo convertido no encontrado")
    
    except Exception as e:
        logger.error(f'Error sirviendo audio convertido {message_id}: {str(e)}')
        raise Http404("Error interno del servidor")


@login_required
@api_require_whatsapp_access
def test_audio_debug(request, message_id):
    """
    API para debug de conversión de audio
    """
    try:
        mensaje = get_object_or_404(Mensaje, id=message_id)
        
        if mensaje.tipo != 'audio':
            return ResponseFormatter.error_response('No es un mensaje de audio', 400)
        
        debug_info = {
            'message_id': message_id,
            'original_file': {
                'exists': bool(mensaje.archivo_local),
                'path': mensaje.archivo_local.path if mensaje.archivo_local else None,
                'url': mensaje.archivo_local.url if mensaje.archivo_local else None,
                'size': mensaje.archivo_tamaño,
                'mime_type': mensaje.archivo_tipo_mime
            },
            'conversion_status': 'not_attempted'
        }
        
        if mensaje.archivo_local:
            # Verificar si archivo original existe
            original_exists = os.path.exists(mensaje.archivo_local.path)
            debug_info['original_file']['file_exists'] = original_exists
            
            if original_exists:
                # Intentar conversión
                success, result = MessageService.convert_audio_to_ogg(message_id)
                
                if success:
                    ogg_exists = os.path.exists(result)
                    debug_info.update({
                        'conversion_status': 'success',
                        'converted_file': {
                            'path': result,
                            'exists': ogg_exists,
                            'size': os.path.getsize(result) if ogg_exists else 0
                        }
                    })
                else:
                    debug_info.update({
                        'conversion_status': 'failed',
                        'error': result
                    })
        
        return ResponseFormatter.success_response(debug_info)
        
    except Exception as e:
        logger.error(f'Error en debug de audio {message_id}: {str(e)}')
        return ResponseFormatter.error_response('Error interno del servidor', 500)


@login_required
@api_require_whatsapp_access
def media_upload_test(request):
    """
    API para probar subida de archivos multimedia
    """
    if request.method == 'POST':
        try:
            uploaded_file = request.FILES.get('test_file')
            
            if not uploaded_file:
                return ResponseFormatter.error_response('No se proporcionó archivo', 400)
            
            # Validar archivo
            from ..utils.formatters import ValidationHelper
            is_valid, error = ValidationHelper.validate_file_upload(uploaded_file)
            
            if not is_valid:
                return ResponseFormatter.error_response(error, 400)
            
            # Guardar archivo temporalmente
            temp_path = f'temp_test/{uploaded_file.name}'
            saved_path = default_storage.save(temp_path, uploaded_file)
            file_url = request.build_absolute_uri(default_storage.url(saved_path))
            
            # Información del archivo
            file_info = {
                'name': uploaded_file.name,
                'size': uploaded_file.size,
                'content_type': uploaded_file.content_type,
                'saved_path': saved_path,
                'url': file_url
            }
            
            # Verificar accesibilidad de la URL
            try:
                import requests
                response = requests.head(file_url, timeout=5)
                file_info['url_accessible'] = response.status_code == 200
                file_info['url_status_code'] = response.status_code
            except Exception as url_error:
                file_info['url_accessible'] = False
                file_info['url_error'] = str(url_error)
            
            return ResponseFormatter.success_response(file_info, 'Archivo subido exitosamente')
            
        except Exception as e:
            logger.error(f'Error en test de subida: {str(e)}')
            return ResponseFormatter.error_response('Error interno del servidor', 500)
    
    else:
        return ResponseFormatter.success_response({
            'upload_url': request.build_absolute_uri(),
            'max_size_mb': 16,
            'allowed_types': [
                'image/jpeg', 'image/png', 'image/gif',
                'audio/mpeg', 'audio/mp4', 'audio/ogg',
                'video/mp4', 'video/mpeg',
                'application/pdf', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]
        })


@login_required
@api_require_whatsapp_access
def cleanup_temp_files(request):
    """
    API para limpiar archivos temporales
    """
    if request.method == 'POST':
        try:
            import glob
            
            # Limpiar archivos temporales de WhatsApp
            temp_patterns = [
                os.path.join(settings.MEDIA_ROOT, 'temp_whatsapp', '*'),
                os.path.join(settings.MEDIA_ROOT, 'temp_test', '*')
            ]
            
            cleaned_files = 0
            total_size = 0
            
            for pattern in temp_patterns:
                files = glob.glob(pattern)
                for file_path in files:
                    try:
                        if os.path.isfile(file_path):
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleaned_files += 1
                            total_size += file_size
                    except Exception as file_error:
                        logger.warning(f'Error eliminando archivo {file_path}: {file_error}')
            
            return ResponseFormatter.success_response({
                'cleaned_files': cleaned_files,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }, f'Limpieza completada: {cleaned_files} archivos eliminados')
            
        except Exception as e:
            logger.error(f'Error en limpieza de archivos: {str(e)}')
            return ResponseFormatter.error_response('Error interno del servidor', 500)
    
    else:
        # Obtener información de archivos temporales
        try:
            import glob
            
            temp_patterns = [
                os.path.join(settings.MEDIA_ROOT, 'temp_whatsapp', '*'),
                os.path.join(settings.MEDIA_ROOT, 'temp_test', '*')
            ]
            
            temp_files = []
            total_size = 0
            
            for pattern in temp_patterns:
                files = glob.glob(pattern)
                for file_path in files:
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        temp_files.append({
                            'path': file_path,
                            'name': os.path.basename(file_path),
                            'size': file_size,
                            'modified': os.path.getmtime(file_path)
                        })
            
            return ResponseFormatter.success_response({
                'temp_files': temp_files,
                'total_files': len(temp_files),
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            })
            
        except Exception as e:
            logger.error(f'Error obteniendo info de archivos: {str(e)}')
            return ResponseFormatter.error_response('Error interno del servidor', 500)