from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_http_methods
import json
import csv
from io import StringIO

from .models import EventoComercial, InvitacionQR, VisitaEvento, EstadisticaEvento
from .forms import EventoComercialForm, VisitaEventoForm

User = get_user_model()


@login_required
def eventos_list(request):
    """Lista de eventos comerciales"""
    eventos = EventoComercial.objects.all()
    
    # Filtros
    search = request.GET.get('search', '').strip()
    activo = request.GET.get('activo')
    
    if search:
        eventos = eventos.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search) |
            Q(ubicacion__icontains=search)
        )
    
    if activo and activo != 'todos':
        eventos = eventos.filter(activo=(activo == 'true'))
    
    # Paginación
    paginator = Paginator(eventos, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'activo_seleccionado': activo,
        'title': 'Eventos Comerciales',
    }
    return render(request, 'events/eventos/list.html', context)


@login_required
@permission_required('events.add_eventocomercial', raise_exception=True)
def evento_create(request):
    """Crear nuevo evento comercial"""
    if request.method == 'POST':
        form = EventoComercialForm(request.POST)
        if form.is_valid():
            evento = form.save(commit=False)
            evento.creado_por = request.user
            evento.save()
            
            # Crear estadísticas iniciales
            EstadisticaEvento.objects.create(evento=evento)
            
            messages.success(request, f'Evento "{evento.nombre}" creado exitosamente.')
            return redirect('events:evento_detail', pk=evento.pk)
    else:
        form = EventoComercialForm()
    
    context = {
        'form': form,
        'title': 'Crear Evento Comercial',
    }
    return render(request, 'events/eventos/form.html', context)


@login_required
def evento_detail(request, pk):
    """Detalle de evento comercial"""
    evento = get_object_or_404(EventoComercial, pk=pk)
    
    # Estadísticas del evento
    stats = {
        'total_invitaciones': evento.invitaciones.count(),
        'total_visitas': VisitaEvento.objects.filter(invitacion__evento=evento).count(),
        'invitaciones_activas': evento.invitaciones.filter(activa=True).count(),
        'visitas_hoy': VisitaEvento.objects.filter(
            invitacion__evento=evento,
            fecha_visita__date=timezone.now().date()
        ).count(),
    }
    
    # Últimas visitas
    ultimas_visitas = VisitaEvento.objects.filter(
        invitacion__evento=evento
    ).select_related('invitacion__vendedor').order_by('-fecha_visita')[:10]
    
    context = {
        'evento': evento,
        'stats': stats,
        'ultimas_visitas': ultimas_visitas,
        'title': f'Evento: {evento.nombre}',
    }
    return render(request, 'events/eventos/detail.html', context)


@login_required
@permission_required('events.change_eventocomercial', raise_exception=True)
def evento_edit(request, pk):
    """Editar evento comercial"""
    evento = get_object_or_404(EventoComercial, pk=pk)
    
    if request.method == 'POST':
        form = EventoComercialForm(request.POST, instance=evento)
        if form.is_valid():
            form.save()
            messages.success(request, f'Evento "{evento.nombre}" actualizado exitosamente.')
            return redirect('events:evento_detail', pk=evento.pk)
    else:
        form = EventoComercialForm(instance=evento)
    
    context = {
        'form': form,
        'evento': evento,
        'title': f'Editar Evento: {evento.nombre}',
    }
    return render(request, 'events/eventos/form.html', context)


@login_required
@permission_required('events.delete_eventocomercial', raise_exception=True)
def evento_delete(request, pk):
    """Eliminar evento comercial"""
    evento = get_object_or_404(EventoComercial, pk=pk)
    
    if request.method == 'POST':
        evento_nombre = evento.nombre
        evento.delete()
        messages.success(request, f'Evento "{evento_nombre}" eliminado exitosamente.')
        return redirect('events:eventos_list')
    
    context = {
        'evento': evento,
        'title': f'Eliminar Evento: {evento.nombre}',
        'can_delete': not evento.invitaciones.exists(),
    }
    return render(request, 'events/eventos/delete.html', context)


@login_required
def generar_qr(request, evento_id):
    """Generar QR para un vendedor en un evento específico"""
    evento = get_object_or_404(EventoComercial, pk=evento_id)
    
    if not evento.permite_invitaciones:
        messages.error(request, 'Este evento no permite generar invitaciones.')
        return redirect('events:evento_detail', pk=evento_id)
    
    # Verificar si ya tiene una invitación para este evento
    invitacion, created = InvitacionQR.objects.get_or_create(
        evento=evento,
        vendedor=request.user,
        defaults={
            'usos_maximos': 999999,  # Sin límite por defecto
        }
    )
    
    if created:
        messages.success(request, 'QR de invitación generado exitosamente.')
    else:
        messages.info(request, 'Ya tienes un QR para este evento.')
    
    return redirect('events:evento_detail', pk=evento_id)


@login_required
def descargar_qr(request, codigo_qr):
    """Descargar imagen QR"""
    invitacion = get_object_or_404(InvitacionQR, codigo_qr=codigo_qr)
    
    # Verificar que el usuario puede descargar este QR
    if invitacion.vendedor != request.user and not request.user.has_perm('events.view_invitacionqr'):
        raise Http404("No tienes permiso para descargar este QR")
    
    if not invitacion.archivo_qr:
        invitacion.generar_qr()
    
    response = HttpResponse(invitacion.archivo_qr.read(), content_type='image/png')
    filename = f'QR_{invitacion.evento.nombre}_{invitacion.vendedor.get_full_name()}.png'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


def qr_info(request, codigo_qr):
    """Vista pública para mostrar información del QR (clientes con teléfonos)"""
    try:
        invitacion = InvitacionQR.objects.select_related('evento', 'vendedor').get(
            codigo_qr=codigo_qr
        )
        
        # Incrementar contador de vistas solo si no es un bot o crawler
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_bot = any(bot in user_agent for bot in ['bot', 'crawl', 'spider', 'scraper'])
        
        if not is_bot:
            # Usar F() para evitar race conditions
            from django.db.models import F
            InvitacionQR.objects.filter(codigo_qr=codigo_qr).update(
                vistas_qr=F('vistas_qr') + 1
            )
            # Refrescar el objeto para obtener el valor actualizado
            invitacion.refresh_from_db()
        
        # Construir URL de descarga para compartir
        download_url = request.build_absolute_uri(
            f'/events/invitation/{invitacion.codigo_qr}/download/'
        ).replace('http://', 'https://')
        
        context = {
            'invitacion': invitacion,
            'evento': invitacion.evento,
            'vendedor': invitacion.vendedor,
            'equipo': invitacion.get_equipo_vendedor(),
            'download_url': download_url,
            'es_vista_publica': True,  # Para distinguir del scanner interno
        }
        return render(request, 'events/public/qr_info.html', context)
        
    except InvitacionQR.DoesNotExist:
        context = {
            'error': 'Código QR no válido o expirado.',
            'error_detail': 'El código QR que intentas acceder no existe o ha sido desactivado.',
        }
        return render(request, 'events/public/qr_error.html', context)


# =============================================================================
# VISTAS PÚBLICAS (Sin autenticación requerida)
# =============================================================================

def public_qr_info(request, codigo_qr):
    """Vista alternativa completamente pública para información del QR"""
    try:
        invitacion = InvitacionQR.objects.select_related('evento', 'vendedor').get(
            codigo_qr=codigo_qr
        )
        
        # Incrementar contador de vistas solo si no es un bot o crawler
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        is_bot = any(bot in user_agent for bot in ['bot', 'crawl', 'spider', 'scraper'])
        
        if not is_bot:
            # Usar F() para evitar race conditions
            from django.db.models import F
            InvitacionQR.objects.filter(codigo_qr=codigo_qr).update(
                vistas_qr=F('vistas_qr') + 1
            )
            # Refrescar el objeto para obtener el valor actualizado
            invitacion.refresh_from_db()
        
        # Construir URL de descarga para compartir
        download_url = request.build_absolute_uri(
            f'/events/invitation/{invitacion.codigo_qr}/download/'
        ).replace('http://', 'https://')
        
        context = {
            'invitacion': invitacion,
            'evento': invitacion.evento,
            'vendedor': invitacion.vendedor,
            'equipo': invitacion.get_equipo_vendedor(),
            'download_url': download_url,
            'es_vista_publica': True,
        }
        return render(request, 'events/public/qr_info.html', context)
        
    except InvitacionQR.DoesNotExist:
        context = {
            'error': 'Código QR no válido o expirado.',
            'error_detail': 'El código QR que intentas acceder no existe o ha sido desactivado.',
        }
        return render(request, 'events/public/qr_error.html', context)


def test_public_view(request, codigo_qr):
    """Vista de prueba completamente pública sin dependencias"""
    from django.http import HttpResponse
    return HttpResponse(f"""
    <!DOCTYPE html>
    <html>
    <head><title>Prueba Pública</title></head>
    <body>
        <h1>🎉 Vista pública funcionando!</h1>
        <p>Código QR: {codigo_qr}</p>
        <p>Esta vista NO requiere autenticación</p>
        <p>Si ves esto, el problema está en otra parte</p>
    </body>
    </html>
    """)


def scan_qr(request, codigo_qr):
    """Página de escaneo de QR (sin login requerido)"""
    try:
        invitacion = InvitacionQR.objects.select_related('evento', 'vendedor').get(
            codigo_qr=codigo_qr
        )
        
        if not invitacion.puede_usar:
            context = {
                'error': 'Esta invitación no está disponible o ha expirado.',
                'invitacion': invitacion,
            }
            return render(request, 'events/scan/error.html', context)
        
        if not invitacion.evento.esta_activo:
            context = {
                'error': 'Este evento no está activo en este momento.',
                'invitacion': invitacion,
            }
            return render(request, 'events/scan/error.html', context)
        
        context = {
            'invitacion': invitacion,
            'evento': invitacion.evento,
            'vendedor': invitacion.vendedor,
            'form': VisitaEventoForm(),
        }
        return render(request, 'events/scan/register.html', context)
        
    except InvitacionQR.DoesNotExist:
        context = {
            'error': 'Código QR no válido.',
        }
        return render(request, 'events/scan/error.html', context)


def registrar_visita(request):
    """Registrar visita desde QR (sin login requerido)"""
    if request.method != 'POST':
        return redirect('events:eventos_list')
    
    codigo_qr = request.POST.get('codigo_qr')
    if not codigo_qr:
        messages.error(request, 'Código QR no válido.')
        return redirect('events:eventos_list')
    
    try:
        invitacion = InvitacionQR.objects.get(codigo_qr=codigo_qr)
        
        if not invitacion.puede_usar:
            messages.error(request, 'Esta invitación no está disponible.')
            return redirect('events:scan_qr', codigo_qr=codigo_qr)
        
        form = VisitaEventoForm(request.POST)
        if form.is_valid():
            visita = form.save(commit=False)
            visita.invitacion = invitacion
            visita.registrado_por = request.user if request.user.is_authenticated else None
            
            try:
                visita.save()
                
                context = {
                    'success': True,
                    'visita': visita,
                    'vendedor': invitacion.vendedor,
                    'evento': invitacion.evento,
                }
                return render(request, 'events/scan/success.html', context)
                
            except Exception as e:
                if 'unique constraint' in str(e).lower():
                    messages.error(request, 'Este cliente ya está registrado para este evento.')
                else:
                    messages.error(request, 'Error al registrar la visita.')
                
                return redirect('events:scan_qr', codigo_qr=codigo_qr)
        else:
            messages.error(request, 'Por favor completa todos los campos requeridos.')
            return redirect('events:scan_qr', codigo_qr=codigo_qr)
            
    except InvitacionQR.DoesNotExist:
        messages.error(request, 'Código QR no válido.')
        return redirect('events:eventos_list')


@login_required
def invitaciones_list(request, evento_id):
    """Lista de invitaciones de un evento"""
    evento = get_object_or_404(EventoComercial, pk=evento_id)
    
    invitaciones = evento.invitaciones.select_related('vendedor').annotate(
        total_visitas=Count('visitas')
    ).order_by('-fecha_creacion')
    
    context = {
        'evento': evento,
        'invitaciones': invitaciones,
        'title': f'Invitaciones - {evento.nombre}',
    }
    return render(request, 'events/invitaciones/list.html', context)


@login_required
def evento_reports(request, evento_id):
    """Reportes de un evento"""
    evento = get_object_or_404(EventoComercial, pk=evento_id)
    
    # Estadísticas generales
    visitas = VisitaEvento.objects.filter(invitacion__evento=evento)
    
    stats = {
        'total_invitaciones': evento.invitaciones.count(),
        'total_visitas': visitas.count(),
        'clientes_unicos': visitas.values('cedula_cliente').distinct().count(),
        'conversion_rate': 0,
    }
    
    if stats['total_invitaciones'] > 0:
        stats['conversion_rate'] = (stats['total_visitas'] / stats['total_invitaciones']) * 100
    
    # Estadísticas por vendedor
    vendedores_stats = []
    for invitacion in evento.invitaciones.select_related('vendedor').annotate(
        total_visitas=Count('visitas')
    ):
        vendedores_stats.append({
            'vendedor': invitacion.vendedor,
            'invitaciones': 1,
            'visitas': invitacion.total_visitas,
            'conversion': (invitacion.total_visitas / 1) * 100 if invitacion.total_visitas > 0 else 0,
        })
    
    # Visitas recientes
    visitas_recientes = visitas.select_related(
        'invitacion__vendedor'
    ).order_by('-fecha_visita')[:20]
    
    context = {
        'evento': evento,
        'stats': stats,
        'vendedores_stats': vendedores_stats,
        'visitas_recientes': visitas_recientes,
        'title': f'Reportes - {evento.nombre}',
    }
    return render(request, 'events/reportes/detail.html', context)


@login_required
def export_visitas(request, evento_id):
    """Exportar visitas de un evento a CSV"""
    evento = get_object_or_404(EventoComercial, pk=evento_id)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="visitas_{evento.nombre}_{timezone.now().strftime("%Y%m%d")}.csv"'
    response.write('\ufeff')  # BOM para Excel
    
    writer = csv.writer(response)
    writer.writerow([
        'Nombre Cliente', 'Cédula', 'Teléfono', 'Email',
        'Vendedor', 'Fecha Visita', 'Estado', 'Observaciones'
    ])
    
    visitas = VisitaEvento.objects.filter(
        invitacion__evento=evento
    ).select_related('invitacion__vendedor').order_by('-fecha_visita')
    
    for visita in visitas:
        writer.writerow([
            visita.nombre_cliente,
            visita.cedula_cliente,
            visita.telefono_cliente,
            visita.email_cliente,
            visita.vendedor.get_full_name() or visita.vendedor.username,
            visita.fecha_visita.strftime('%d/%m/%Y %H:%M'),
            visita.get_estado_display(),
            visita.observaciones,
        ])
    
    return response


@login_required
def user_qr_codes(request):
    """API: QR codes del usuario actual para mostrar en el perfil"""
    eventos_activos = EventoComercial.objects.filter(
        activo=True,
        permite_invitaciones=True,
        fecha_fin__gte=timezone.now()
    ).order_by('fecha_inicio')
    
    qr_codes = []
    for evento in eventos_activos:
        invitacion, created = InvitacionQR.objects.get_or_create(
            evento=evento,
            vendedor=request.user,
            defaults={'usos_maximos': 999999}
        )
        
        qr_codes.append({
            'evento_id': evento.id,
            'evento_nombre': evento.nombre,
            'evento_fecha': evento.fecha_inicio.strftime('%d/%m/%Y'),
            'codigo_qr': str(invitacion.codigo_qr),
            'download_url': request.build_absolute_uri(
                f'/events/invitation/{invitacion.codigo_qr}/download/'
            ).replace('http://', 'https://'),
            'visitas': invitacion.visitas.count(),
            'vistas_qr': invitacion.vistas_qr,
        })
    
    return JsonResponse({'qr_codes': qr_codes})


# AJAX Views
@login_required
def ajax_validate_qr(request):
    """Validar código QR via AJAX"""
    codigo_qr = request.GET.get('codigo_qr')
    if not codigo_qr:
        return JsonResponse({'valid': False, 'error': 'Código QR requerido'})
    
    try:
        invitacion = InvitacionQR.objects.select_related('evento', 'vendedor').get(
            codigo_qr=codigo_qr
        )
        
        return JsonResponse({
            'valid': invitacion.puede_usar,
            'evento': invitacion.evento.nombre,
            'vendedor': invitacion.vendedor.get_full_name() or invitacion.vendedor.username,
            'can_use': invitacion.puede_usar,
        })
    except InvitacionQR.DoesNotExist:
        return JsonResponse({'valid': False, 'error': 'Código QR no válido'})


@login_required
def ajax_search_client(request):
    """Buscar cliente por cédula via AJAX"""
    cedula = request.GET.get('cedula')
    if not cedula:
        return JsonResponse({'found': False})
    
    # Buscar en visitas anteriores
    visita = VisitaEvento.objects.filter(cedula_cliente=cedula).first()
    if visita:
        return JsonResponse({
            'found': True,
            'nombre': visita.nombre_cliente,
            'telefono': visita.telefono_cliente,
            'email': visita.email_cliente,
        })
    
    return JsonResponse({'found': False})


# =============================================================================
# MÓDULO DE ESCÁNER PARA PERSONAL DE RECEPCIÓN
# =============================================================================

@login_required
def scanner_dashboard(request):
    """Dashboard principal del escáner para personal de recepción"""
    # Obtener eventos activos
    eventos_activos = EventoComercial.objects.filter(
        activo=True,
        fecha_inicio__lte=timezone.now(),
        fecha_fin__gte=timezone.now()
    ).order_by('fecha_inicio')
    
    # Estadísticas del día
    hoy = timezone.now().date()
    visitas_hoy = VisitaEvento.objects.filter(
        fecha_visita__date=hoy
    ).count()
    
    # Últimos escaneos
    ultimos_escaneos = VisitaEvento.objects.select_related(
        'invitacion__evento', 'invitacion__vendedor'
    ).order_by('-fecha_visita')[:10]
    
    context = {
        'eventos_activos': eventos_activos,
        'visitas_hoy': visitas_hoy,
        'ultimos_escaneos': ultimos_escaneos,
    }
    return render(request, 'events/scanner/dashboard.html', context)


@require_http_methods(["GET", "POST"])
def scanner_scan(request):
    """Vista para escanear códigos QR desde el dashboard del escáner"""
    if request.method == 'GET':
        return render(request, 'events/scanner/scan.html')
    
    # POST: procesar escaneo
    codigo_qr = request.POST.get('codigo_qr', '').strip()
    
    if not codigo_qr:
        return JsonResponse({
            'success': False,
            'error': 'Código QR no proporcionado'
        })
    
    try:
        # Validar formato UUID
        import uuid
        codigo_uuid = uuid.UUID(codigo_qr)
        
        # Buscar la invitación
        invitacion = InvitacionQR.objects.select_related('evento', 'vendedor').get(
            codigo_qr=codigo_uuid
        )
        
        # Preparar información del QR
        qr_info = {
            'success': True,
            'evento': {
                'nombre': invitacion.evento.nombre,
                'ubicacion': invitacion.evento.ubicacion,
                'fecha_inicio': invitacion.evento.fecha_inicio.strftime('%d/%m/%Y %H:%M'),
                'descripcion': invitacion.evento.descripcion or 'Sin descripción'
            },
            'vendedor': {
                'nombre': invitacion.vendedor.get_full_name() or invitacion.vendedor.username,
                'email': invitacion.vendedor.email or 'Sin email'
            },
            'equipo': invitacion.get_equipo_vendedor(),
            'estado': {
                'activo': invitacion.activa,
                'usos': f"{invitacion.usos_actuales}/{invitacion.usos_maximos}",
                'puede_usar': invitacion.puede_usar,
                'fecha_creacion': invitacion.fecha_creacion.strftime('%d/%m/%Y %H:%M')
            },
            'url_registro': f"/events/scan/{codigo_uuid}/",
            'url_info': f"/events/info/{codigo_uuid}/"
        }
        
        return JsonResponse(qr_info)
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Formato de código QR inválido'
        })
    except InvitacionQR.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Código QR no encontrado en el sistema'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error interno: {str(e)}'
        })