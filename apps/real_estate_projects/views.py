# apps/real_estate_projects/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
import json
from .models import (
    Proyecto, Fase, Torre, Piso, Sector, Manzana, Inmueble,
    GerenteProyecto, JefeProyecto, Ponderador
)

User = get_user_model()

@login_required
def projects_dashboard(request):
    """Dashboard de proyectos con información completa y estadísticas útiles"""
    from django.db.models import Avg, Sum, Case, When, Value, IntegerField
    from decimal import Decimal
    
    # Estadísticas principales
    proyectos_activos = Proyecto.objects.filter(activo=True)
    inmuebles_totales = Inmueble.objects.filter(disponible=True, fase__activo=True, fase__proyecto__activo=True)
    
    stats = {
        'total_proyectos': proyectos_activos.count(),
        'total_inmuebles': inmuebles_totales.count(),
        'proyectos_departamentos': proyectos_activos.filter(tipo='departamentos').count(),
        'proyectos_terrenos': proyectos_activos.filter(tipo='terrenos').count(),
        
        # Estadísticas de comercialización
        'inmuebles_disponibles': inmuebles_totales.filter(estado='disponible').count(),
        'inmuebles_reservados': inmuebles_totales.filter(estado='reservado').count(),
        'inmuebles_vendidos': inmuebles_totales.filter(estado='vendido').count(),
        'inmuebles_comercializables': inmuebles_totales.filter(disponible_comercializacion=True).count(),
        
        # Estadísticas de área y precios
        'area_total_m2': inmuebles_totales.aggregate(total=Sum('m2'))['total'] or 0,
        'area_promedio_m2': inmuebles_totales.aggregate(avg=Avg('m2'))['avg'] or 0,
        
        # Ponderadores activos
        'total_ponderadores': Ponderador.objects.filter(activo=True).count(),
        'ponderadores_proyecto': Ponderador.objects.filter(activo=True, nivel_aplicacion='proyecto').count(),
        'ponderadores_fase': Ponderador.objects.filter(activo=True, nivel_aplicacion='fase').count(),
        'ponderadores_inmueble': Ponderador.objects.filter(activo=True, nivel_aplicacion='inmueble').count(),
    }
    
    # Calcular porcentajes
    if stats['total_inmuebles'] > 0:
        stats['porcentaje_vendidos'] = round((stats['inmuebles_vendidos'] / stats['total_inmuebles']) * 100, 1)
        stats['porcentaje_disponibles'] = round((stats['inmuebles_disponibles'] / stats['total_inmuebles']) * 100, 1)
        stats['porcentaje_comercializables'] = round((stats['inmuebles_comercializables'] / stats['total_inmuebles']) * 100, 1)
    else:
        stats['porcentaje_vendidos'] = 0
        stats['porcentaje_disponibles'] = 0
        stats['porcentaje_comercializables'] = 0
    
    # Estadísticas por proyecto con rendimiento
    proyectos_stats = []
    for proyecto in proyectos_activos.select_related().prefetch_related('fases')[:8]:
        inmuebles_proyecto = proyecto.fases.filter(activo=True).aggregate(
            total=Count('inmuebles', filter=Q(inmuebles__disponible=True)),
            vendidos=Count('inmuebles', filter=Q(inmuebles__estado='vendido', inmuebles__disponible=True)),
            disponibles=Count('inmuebles', filter=Q(inmuebles__estado='disponible', inmuebles__disponible=True)),
            comercializables=Count('inmuebles', filter=Q(inmuebles__disponible_comercializacion=True, inmuebles__disponible=True))
        )
        
        total_inmuebles = inmuebles_proyecto['total'] or 0
        vendidos = inmuebles_proyecto['vendidos'] or 0
        
        proyectos_stats.append({
            'proyecto': proyecto,
            'total_inmuebles': total_inmuebles,
            'inmuebles_vendidos': vendidos,
            'inmuebles_disponibles': inmuebles_proyecto['disponibles'] or 0,
            'inmuebles_comercializables': inmuebles_proyecto['comercializables'] or 0,
            'porcentaje_vendido': round((vendidos / total_inmuebles) * 100, 1) if total_inmuebles > 0 else 0,
            'total_fases': proyecto.fases.filter(activo=True).count(),
        })
    
    # Proyectos recientes (últimos 5)
    proyectos_recientes = proyectos_activos.order_by('-created_at')[:5]
    
    # Actividad reciente - inmuebles vendidos recientemente
    inmuebles_vendidos_recientes = Inmueble.objects.filter(
        estado='vendido',
        disponible=True,
        fase__activo=True,
        fase__proyecto__activo=True
    ).select_related('fase', 'fase__proyecto').order_by('-updated_at')[:10]
    
    # Estadísticas de tipos de inmuebles
    tipos_stats = inmuebles_totales.values('tipo').annotate(
        total=Count('id'),
        vendidos=Count(Case(When(estado='vendido', then=1), output_field=IntegerField())),
        disponibles=Count(Case(When(estado='disponible', then=1), output_field=IntegerField())),
        comercializables=Count(Case(When(disponible_comercializacion=True, then=1), output_field=IntegerField()))
    ).order_by('tipo')
    
    # Rendimiento por fase (top 10 fases con más ventas)
    fases_top_ventas = Fase.objects.filter(activo=True, proyecto__activo=True).annotate(
        total_inmuebles=Count('inmuebles', filter=Q(inmuebles__disponible=True)),
        vendidos=Count('inmuebles', filter=Q(inmuebles__estado='vendido', inmuebles__disponible=True))
    ).filter(vendidos__gt=0).order_by('-vendidos')[:10]
    
    context = {
        'title': 'Dashboard de Proyectos Inmobiliarios',
        'stats': stats,
        'proyectos_stats': proyectos_stats,
        'proyectos_recientes': proyectos_recientes,
        'inmuebles_vendidos_recientes': inmuebles_vendidos_recientes,
        'tipos_stats': tipos_stats,
        'fases_top_ventas': fases_top_ventas,
        'show_activity': True,  # Flag para mostrar sección de actividad reciente
        'show_performance': True,  # Flag para mostrar métricas de rendimiento
    }
    
    return render(request, 'real_estate_projects/dashboard.html', context)

@login_required
def proyectos_list(request):
    """Lista de proyectos"""
    # Obtener proyectos con prefetch para optimizar consultas
    proyectos = Proyecto.objects.filter(activo=True).prefetch_related('fases')
    
    # Búsqueda
    search = request.GET.get('search', '')
    if search:
        proyectos = proyectos.filter(
            Q(nombre__icontains=search) |
            Q(descripcion__icontains=search)
        )
    
    # Filtro por tipo
    tipo_filter = request.GET.get('tipo', '')
    if tipo_filter:
        proyectos = proyectos.filter(tipo=tipo_filter)
    
    # Paginación
    paginator = Paginator(proyectos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener tipos de proyecto de forma segura
    tipos_proyecto = getattr(Proyecto, 'TIPOS_PROYECTO', [
        ('departamentos', 'Departamentos'),
        ('terrenos', 'Terrenos')
    ])
    
    return render(request, 'real_estate_projects/proyectos/list.html', {
        'title': 'Gestión de Proyectos',
        'page_obj': page_obj,
        'search': search,
        'tipo_filter': tipo_filter,
        'tipos_proyecto': tipos_proyecto,
    })

@login_required
def proyectos_create(request):
    """Crear proyecto"""
    from .forms import ProyectoForm
    from django.db import transaction
    
    if request.method == 'POST':
        form = ProyectoForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear el proyecto
                    proyecto = form.save()
                    
                    # Información simple para verificar
                    dynamic_structure_data = form.cleaned_data.get('dynamic_structure_data', {})
                    fases_data = dynamic_structure_data.get('fases', {})
                    
                    # Preparar datos para create_project_structure incluyendo user_id
                    form_data_with_user = form.cleaned_data.copy()
                    form_data_with_user['user_id'] = request.user.id
                    
                    # Crear la estructura completa del proyecto
                    create_project_structure(proyecto, form_data_with_user)
                    
                    total_inmuebles = count_total_properties(form.cleaned_data)
                    num_fases = len(dynamic_structure_data.get('fases', {}))
                    
                    # Verificar cuántas fases se crearon realmente
                    fases_creadas = proyecto.fases.count()
                    messages.info(request, f"DEBUG: Se crearon {fases_creadas} fases en la base de datos")
                    
                    messages.success(request, f'Proyecto "{proyecto.nombre}" creado exitosamente con {num_fases} fase{"s" if num_fases != 1 else ""} y {total_inmuebles} inmuebles.')
                    return redirect('projects:list')
                    
            except Exception as e:
                messages.error(request, f'Error al crear el proyecto: {str(e)}')
                
    else:
        form = ProyectoForm()
    
    return render(request, 'real_estate_projects/proyectos/form.html', {
        'title': 'Crear Proyecto',
        'form': form,
        'is_create': True,
    })

@login_required
def proyectos_detail(request, pk):
    """Detalle de proyecto"""
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    fases = proyecto.fases.filter(activo=True).order_by('numero_fase')
    
    # Ponderadores del proyecto
    ponderadores_proyecto = proyecto.ponderadores.filter(activo=True, nivel_aplicacion='proyecto').order_by('nombre')
    
    # Estadísticas del proyecto
    stats = {
        'total_fases': fases.count(),
        'total_inmuebles': proyecto.total_inmuebles,
        'inmuebles_disponibles': proyecto.inmuebles_disponibles,
        'inmuebles_vendidos': proyecto.inmuebles_vendidos,
        'porcentaje_vendido': proyecto.porcentaje_vendido,
        'total_torres': Torre.objects.filter(
            fase__proyecto=proyecto, activo=True
        ).count() if proyecto.tipo == 'departamentos' else 0,
        'total_sectores': Sector.objects.filter(
            fase__proyecto=proyecto, activo=True
        ).count() if proyecto.tipo == 'terrenos' else 0,
    }
    
    # Datos detallados por fase
    fases_data = []
    for fase in fases:
        fase_info = {
            'fase': fase,
            'ponderadores': fase.ponderadores.filter(activo=True).order_by('nombre'),
            'inmuebles_sample': fase.inmuebles.filter(disponible=True)[:5],  # Muestra de inmuebles
        }
        
        if proyecto.tipo == 'departamentos':
            fase_info['torres'] = Torre.objects.filter(fase=fase, activo=True).order_by('numero_torre')
        else:
            fase_info['sectores'] = Sector.objects.filter(fase=fase, activo=True).order_by('numero_sector')
        
        fases_data.append(fase_info)
    
    return render(request, 'real_estate_projects/proyectos/detail.html', {
        'title': f'Proyecto: {proyecto.nombre}',
        'proyecto': proyecto,
        'fases': fases,
        'fases_data': fases_data,
        'ponderadores_proyecto': ponderadores_proyecto,
        'stats': stats,
    })

@login_required
def proyectos_edit(request, pk):
    """Editar proyecto"""
    from .forms import ProyectoForm
    from django.db import transaction
    import sys
    
    print(f"*** ENTRANDO A proyectos_edit - PK: {pk} ***", file=sys.stderr)
    proyecto = get_object_or_404(Proyecto, pk=pk, activo=True)
    print(f"*** PROYECTO ENCONTRADO: {proyecto.nombre} ***", file=sys.stderr)
    
    if request.method == 'POST':
        print(f"*** MÉTODO POST DETECTADO ***", file=sys.stderr)
        form = ProyectoForm(request.POST, instance=proyecto)
        print(f"*** FORMULARIO CREADO ***", file=sys.stderr)
        if form.is_valid():
            print(f"*** FORMULARIO VÁLIDO ***", file=sys.stderr)
            try:
                with transaction.atomic():
                    # Guardar el proyecto editado
                    proyecto = form.save()
                    print(f"*** PROYECTO GUARDADO: {proyecto.nombre} ***", file=sys.stderr)
                    
                    # Si hay datos de estructura dinámica, procesar cambios en la estructura
                    dynamic_structure_data = form.cleaned_data.get('dynamic_structure_data', {})
                    
                    # Procesar ponderadores (nuevos y existentes) independientemente de las fases
                    ponderadores_nuevos = dynamic_structure_data.get('ponderadores', [])
                    ponderadores_existentes = dynamic_structure_data.get('existing_ponderadores', [])
                    ponderadores_fase = dynamic_structure_data.get('ponderadores_fase', [])
                    
                    if ponderadores_nuevos or ponderadores_existentes or ponderadores_fase:
                        print(f"*** ENCONTRADOS PONDERADORES PARA PROCESAR ***", file=sys.stderr)
                        print(f"*** NUEVOS: {len(ponderadores_nuevos)} ***", file=sys.stderr) 
                        print(f"*** EXISTENTES: {len(ponderadores_existentes)} ***", file=sys.stderr)
                        print(f"*** FASE: {len(ponderadores_fase)} ***", file=sys.stderr)
                        # Procesar solo ponderadores
                        process_ponderadores_only(proyecto, dynamic_structure_data, request.user.id)
                    else:
                        print(f"*** NO HAY PONDERADORES PARA PROCESAR ***", file=sys.stderr)
                        print(f"*** dynamic_structure_data keys: {list(dynamic_structure_data.keys())} ***", file=sys.stderr)
                    
                    # Procesar comercialización independientemente de las fases
                    fases_data = dynamic_structure_data.get('fases', {})
                    if fases_data:
                        print(f"*** PROCESANDO COMERCIALIZACIÓN ***", file=sys.stderr)
                        process_comercializacion_only(proyecto, dynamic_structure_data)
                    else:
                        print(f"*** NO HAY DATOS DE COMERCIALIZACIÓN ***", file=sys.stderr)
                    
                    if dynamic_structure_data.get('fases'):
                        # Actualizar estructura del proyecto si se proporcionó
                        print(f"*** EJECUTANDO update_project_structure ***", file=sys.stderr)
                        update_project_structure(proyecto, form.cleaned_data, request.user.id)
                        
                        total_inmuebles = count_total_properties(form.cleaned_data)
                        num_fases = len(dynamic_structure_data.get('fases', {}))
                        messages.success(request, f'Proyecto "{proyecto.nombre}" actualizado exitosamente con {num_fases} fase{"s" if num_fases != 1 else ""} y {total_inmuebles} inmuebles.')
                    else:
                        messages.success(request, f'Proyecto "{proyecto.nombre}" actualizado exitosamente.')
                    
                    print(f"*** TRANSACCIÓN COMPLETADA EXITOSAMENTE ***", file=sys.stderr)
                    
                    return redirect('projects:list')
                    
            except Exception as e:
                print(f"*** ERROR EN TRANSACCIÓN: {e} ***", file=sys.stderr)
                messages.error(request, f'Error al actualizar el proyecto: {str(e)}')
        else:
            print(f"*** FORMULARIO INVÁLIDO: {form.errors} ***", file=sys.stderr)
                
    else:
        print(f"*** MÉTODO GET DETECTADO ***", file=sys.stderr)
        # Pre-populate form with existing data including current management assignments
        initial_data = {}
        if proyecto.gerente_proyecto:
            initial_data['gerente_usuario'] = proyecto.gerente_proyecto.usuario
        if proyecto.jefe_proyecto:
            initial_data['jefe_usuario'] = proyecto.jefe_proyecto.usuario
        
        form = ProyectoForm(instance=proyecto, initial=initial_data)
    
    # Preparar datos de estructura existente para pre-cargar en el formulario
    existing_structure = _build_existing_structure_data(proyecto)
    
    # Load existing ponderadores for display (both active and inactive for filtering)
    ponderadores_proyecto = proyecto.ponderadores.filter(nivel_aplicacion='proyecto').order_by('nombre')
    
    # Get phase structure for context
    fases = proyecto.fases.filter(activo=True).order_by('numero_fase')
    
    context = {
        'title': f'Editar Proyecto: {proyecto.nombre}',
        'form': form,
        'is_create': False,
        'proyecto': proyecto,
        'ponderadores_proyecto': ponderadores_proyecto,
        'fases': fases,
        'can_edit_structure': True,  # Allow full structure editing in edit mode
        'existing_structure': json.dumps(existing_structure),  # Pasar estructura existente al template como JSON
    }
    
    return render(request, 'real_estate_projects/proyectos/form.html', context)

@login_required
def proyectos_delete(request, pk):
    """Eliminar proyecto"""
    return render(request, 'real_estate_projects/proyectos/delete.html', {
        'title': 'Eliminar Proyecto',
    })

@login_required
def fases_list(request, proyecto_pk):
    """Lista de fases de un proyecto"""
    return render(request, 'real_estate_projects/fases/list.html', {
        'title': 'Fases del Proyecto',
    })

@login_required
def fases_create(request, proyecto_pk):
    """Crear fase"""
    return render(request, 'real_estate_projects/fases/form.html', {
        'title': 'Crear Fase',
    })

@login_required
def fase_edit(request, pk):
    """Editar fase"""
    return render(request, 'real_estate_projects/fases/form.html', {
        'title': 'Editar Fase',
    })

@login_required
def fase_delete(request, pk):
    """Eliminar fase"""
    return render(request, 'real_estate_projects/fases/delete.html', {
        'title': 'Eliminar Fase',
    })

@login_required
def inmuebles_list(request):
    """Lista general de inmuebles con filtros avanzados"""
    # Obtener todos los inmuebles activos
    inmuebles = Inmueble.objects.select_related(
        'fase', 'fase__proyecto', 'piso', 'piso__torre', 'manzana', 'manzana__sector'
    ).filter(
        disponible=True, 
        fase__activo=True, 
        fase__proyecto__activo=True
    )
    
    # Filtros
    proyecto_id = request.GET.get('proyecto')
    fase_id = request.GET.get('fase')
    estado = request.GET.get('estado')
    tipo = request.GET.get('tipo')
    comercializable = request.GET.get('comercializable')
    search = request.GET.get('search', '')
    
    # Filtro por proyecto
    if proyecto_id:
        inmuebles = inmuebles.filter(fase__proyecto_id=proyecto_id)
    
    # Filtro por fase
    if fase_id:
        inmuebles = inmuebles.filter(fase_id=fase_id)
    
    # Filtro por estado
    if estado:
        inmuebles = inmuebles.filter(estado=estado)
    
    # Filtro por tipo
    if tipo:
        inmuebles = inmuebles.filter(tipo=tipo)
    
    # Filtro por comercializable (ahora solo en inmuebles)
    if comercializable == 'true':
        inmuebles = inmuebles.filter(disponible_comercializacion=True)
    elif comercializable == 'false':
        inmuebles = inmuebles.filter(disponible_comercializacion=False)
    
    # Búsqueda por texto
    if search:
        inmuebles = inmuebles.filter(
            Q(codigo__icontains=search) |
            Q(fase__proyecto__nombre__icontains=search) |
            Q(fase__nombre__icontains=search) |
            Q(caracteristicas__icontains=search)
        )
    
    # Ordenamiento
    order_by = request.GET.get('order_by', 'fase__proyecto__nombre')
    if order_by in ['codigo', 'estado', 'tipo', 'precio_calculado', 'area_total', 'fase__proyecto__nombre']:
        if order_by == 'precio_calculado':
            # Para precio calculado, ordenar por precio_manual primero, luego por cálculo
            inmuebles = inmuebles.extra(
                select={'precio_orden': 'COALESCE(precio_manual, (m2 * precio_m2 * factor_precio))'}
            ).order_by('precio_orden')
        elif order_by == 'area_total':
            inmuebles = inmuebles.extra(
                select={'area_orden': 'm2'}
            ).order_by('area_orden')
        else:
            inmuebles = inmuebles.order_by(order_by)
    
    # Paginación
    paginator = Paginator(inmuebles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Datos para filtros
    proyectos = Proyecto.objects.filter(activo=True).order_by('nombre')
    fases = Fase.objects.filter(activo=True).select_related('proyecto').order_by('proyecto__nombre', 'numero_fase')
    estados = Inmueble.ESTADOS_INMUEBLE
    tipos = Inmueble.TIPOS_INMUEBLE
    
    # Estadísticas
    stats = {
        'total_inmuebles': inmuebles.count(),
        'disponibles': inmuebles.filter(estado='disponible').count(),
        'reservados': inmuebles.filter(estado='reservado').count(),
        'vendidos': inmuebles.filter(estado='vendido').count(),
        'comercializables': inmuebles.filter(disponible_comercializacion=True).count(),
    }
    
    return render(request, 'real_estate_projects/inmuebles/list.html', {
        'title': 'Gestión de Inmuebles',
        'page_obj': page_obj,
        'proyectos': proyectos,
        'fases': fases,
        'estados': estados,
        'tipos': tipos,
        'stats': stats,
        'filters': {
            'proyecto': proyecto_id,
            'fase': fase_id,
            'estado': estado,
            'tipo': tipo,
            'comercializable': comercializable,
            'search': search,
            'order_by': order_by,
        },
    })

@login_required
def inmuebles_by_project(request, proyecto_pk):
    """Inmuebles de un proyecto específico"""
    return render(request, 'real_estate_projects/inmuebles/list.html', {
        'title': 'Inmuebles del Proyecto',
    })

@login_required
def inmueble_create(request, fase_pk=None):
    """Crear inmueble"""
    from .forms import InmuebleForm
    from django.db import transaction
    
    # Obtener proyecto y fase si se pasan como parámetros
    proyecto_id = request.GET.get('proyecto_id')
    fase = None
    
    if fase_pk:
        try:
            fase = get_object_or_404(Fase, pk=fase_pk, activo=True)
            proyecto_id = fase.proyecto.pk
        except Exception:
            messages.error(request, 'La fase especificada no existe o no está activa.')
            return redirect('projects:inmuebles_list')
    
    if request.method == 'POST':
        form = InmuebleForm(request.POST, proyecto_id=proyecto_id, fase_id=fase_pk)
        if form.is_valid():
            try:
                with transaction.atomic():
                    inmueble = form.save()
                    messages.success(request, f'Inmueble "{inmueble.codigo}" creado exitosamente.')
                    
                    # Determinar dónde redirigir basado en el contexto
                    if fase_pk:
                        return redirect('projects:inmuebles_by_project', proyecto_pk=inmueble.fase.proyecto.pk)
                    else:
                        return redirect('projects:inmueble_detail', pk=inmueble.pk)
                        
            except Exception as e:
                messages.error(request, f'Error al crear el inmueble: {str(e)}')
    else:
        form = InmuebleForm(proyecto_id=proyecto_id, fase_id=fase_pk)
    
    context = {
        'title': 'Crear Inmueble',
        'form': form,
        'is_create': True,
    }
    
    # Agregar contexto adicional si hay fase
    if fase:
        context['fase'] = fase
        context['proyecto'] = fase.proyecto
    
    return render(request, 'real_estate_projects/inmuebles/form.html', context)

@login_required
def inmueble_edit(request, pk):
    """Editar inmueble - permite cambiar propiedades básicas y gestionar ponderadores"""
    from .forms import InmuebleEditForm
    from django.db import transaction
    
    inmueble = get_object_or_404(Inmueble, pk=pk, disponible=True)
    
    # Verificar permisos adicionales si es necesario
    if inmueble.estado == 'vendido':
        messages.warning(request, 'No se puede editar un inmueble que ya está vendido.')
        return redirect('projects:inmueble_detail', pk=inmueble.pk)
    
    if request.method == 'POST':
        form = InmuebleEditForm(request.POST, instance=inmueble)
        if form.is_valid():
            try:
                with transaction.atomic():
                    inmueble = form.save()
                    messages.success(request, f'Inmueble "{inmueble.codigo}" actualizado exitosamente.')
                    return redirect('projects:list')
                    
            except Exception as e:
                messages.error(request, f'Error al actualizar el inmueble: {str(e)}')
    else:
        form = InmuebleEditForm(instance=inmueble)
    
    context = {
        'title': f'Editar Inmueble: {inmueble.codigo}',
        'form': form,
        'inmueble': inmueble,
        'is_create': False,
        'proyecto': inmueble.fase.proyecto,
        'fase': inmueble.fase,
    }
    
    return render(request, 'real_estate_projects/inmuebles/form.html', context)

@login_required
def inmueble_detail(request, pk):
    """Detalle de inmueble"""
    inmueble = get_object_or_404(Inmueble, pk=pk, disponible=True)
    
    # Información adicional del inmueble
    context = {
        'title': f'Inmueble: {inmueble.codigo}',
        'inmueble': inmueble,
        'proyecto': inmueble.fase.proyecto,
        'fase': inmueble.fase,
    }
    
    # Agregar información específica según el tipo de proyecto
    if inmueble.fase.proyecto.tipo == 'departamentos' and inmueble.piso:
        context['torre'] = inmueble.piso.torre
        context['piso'] = inmueble.piso
    elif inmueble.fase.proyecto.tipo == 'terrenos' and inmueble.manzana:
        context['sector'] = inmueble.manzana.sector
        context['manzana'] = inmueble.manzana
    
    return render(request, 'real_estate_projects/inmuebles/detail.html', context)

@login_required
def inmueble_delete(request, pk):
    """Eliminar inmueble"""
    inmueble = get_object_or_404(Inmueble, pk=pk, disponible=True)
    
    if request.method == 'POST':
        try:
            inmueble.disponible = False
            inmueble.save()
            messages.success(request, f'Inmueble "{inmueble.codigo}" eliminado exitosamente.')
            return redirect('projects:inmuebles_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar el inmueble: {str(e)}')
    
    return render(request, 'real_estate_projects/inmuebles/delete.html', {
        'title': 'Eliminar Inmueble',
        'inmueble': inmueble,
    })

# Roles de desarrollo views removed - roles are now managed through project creation/editing

# APIs AJAX
@login_required
def ajax_proyectos_search(request):
    """Buscar proyectos vía AJAX"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    proyectos = Proyecto.objects.filter(
        nombre__icontains=query, activo=True
    )[:10]
    
    results = [{'id': p.id, 'text': p.nombre} for p in proyectos]
    return JsonResponse({'results': results})

@login_required
def ajax_fases_by_proyecto(request, proyecto_pk):
    """Obtener fases de un proyecto vía AJAX"""
    try:
        proyecto = Proyecto.objects.get(pk=proyecto_pk, activo=True)
        fases = proyecto.fases.filter(activo=True).values('id', 'nombre', 'numero_fase')
        return JsonResponse({'fases': list(fases)})
    except Proyecto.DoesNotExist:
        return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)

@login_required
def ajax_torres_by_fase(request, fase_pk):
    """Obtener torres de una fase vía AJAX"""
    try:
        fase = Fase.objects.get(pk=fase_pk, activo=True)
        if fase.proyecto.tipo != 'departamentos':
            return JsonResponse({'error': 'Esta fase no es de tipo departamentos'}, status=400)
        
        torres = fase.torres.filter(activo=True).values('id', 'nombre', 'numero_torre')
        return JsonResponse({'torres': list(torres)})
    except Fase.DoesNotExist:
        return JsonResponse({'error': 'Fase no encontrada'}, status=404)

@login_required
def ajax_pisos_by_torre(request, torre_pk):
    """Obtener pisos de una torre vía AJAX"""
    try:
        torre = Torre.objects.get(pk=torre_pk, activo=True)
        pisos = torre.pisos.filter(activo=True).values('id', 'numero_piso')
        return JsonResponse({'pisos': list(pisos)})
    except Torre.DoesNotExist:
        return JsonResponse({'error': 'Torre no encontrada'}, status=404)

@login_required
def ajax_sectores_by_fase(request, fase_pk):
    """Obtener sectores de una fase vía AJAX"""
    try:
        fase = Fase.objects.get(pk=fase_pk, activo=True)
        if fase.proyecto.tipo != 'terrenos':
            return JsonResponse({'error': 'Esta fase no es de tipo terrenos'}, status=400)
        
        sectores = fase.sectores.filter(activo=True).values('id', 'nombre')
        return JsonResponse({'sectores': list(sectores)})
    except Fase.DoesNotExist:
        return JsonResponse({'error': 'Fase no encontrada'}, status=404)

@login_required
def ajax_manzanas_by_sector(request, sector_pk):
    """Obtener manzanas de un sector vía AJAX"""
    try:
        sector = Sector.objects.get(pk=sector_pk, activo=True)
        manzanas = sector.manzanas.filter(activo=True).values('id', 'numero_manzana')
        return JsonResponse({'manzanas': list(manzanas)})
    except Sector.DoesNotExist:
        return JsonResponse({'error': 'Sector no encontrado'}, status=404)

@login_required
def ajax_get_project_type(request, proyecto_pk):
    """Obtener tipo de proyecto vía AJAX"""
    try:
        proyecto = Proyecto.objects.get(pk=proyecto_pk, activo=True)
        return JsonResponse({'tipo': proyecto.tipo})
    except Proyecto.DoesNotExist:
        return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)

@login_required
def ajax_search_users(request):
    """Búsqueda AJAX de usuarios para Select2"""
    term = request.GET.get('term', '').strip()
    page = int(request.GET.get('page', 1))
    page_size = 20  # Resultados por página
    
    # Filtrar usuarios activos
    users = User.objects.filter(is_active=True)
    
    # Aplicar búsqueda si hay término
    if term:
        users = users.filter(
            Q(username__icontains=term) |
            Q(first_name__icontains=term) |
            Q(last_name__icontains=term) |
            Q(email__icontains=term)
        )
    
    # Ordenar por relevancia
    users = users.order_by('first_name', 'last_name', 'username')
    
    # Paginación
    total_count = users.count()
    start = (page - 1) * page_size
    end = start + page_size
    page_users = users[start:end]
    
    # Formatear resultados para Select2
    results = []
    for user in page_users:
        display_name = user.get_full_name().strip()
        if not display_name:
            display_name = user.username
        
        # Mostrar username si hay nombre completo
        text = f"{display_name} ({user.username})" if user.get_full_name().strip() else user.username
        
        results.append({
            'id': user.id,
            'text': text,
            'email': user.email or ''
        })
    
    # Verificar si hay más páginas
    has_more = end < total_count
    
    return JsonResponse({
        'results': results,
        'pagination': {
            'more': has_more
        }
    })


def create_project_structure(proyecto, form_data):
    """VERSIÓN COMPLETA: Crear estructura del proyecto incluyendo ponderadores y comercialización"""
    import sys
    
    print(f"=== DEBUG CREATE_PROJECT_STRUCTURE ===", file=sys.stderr)
    print(f"PROYECTO: {proyecto.nombre}", file=sys.stderr)
    print(f"FORM_DATA COMPLETO: {form_data}", file=sys.stderr)
    
    dynamic_structure_data = form_data.get('dynamic_structure_data', {})
    fases_data = dynamic_structure_data.get('fases', {})
    
    print(f"DYNAMIC_STRUCTURE_DATA: {dynamic_structure_data}", file=sys.stderr)
    print(f"FASES_DATA: {fases_data}", file=sys.stderr)
    print(f"TOTAL FASES A CREAR: {len(fases_data)}", file=sys.stderr)
    
    # 1. PROCESAR PONDERADORES DEL PROYECTO (NUEVOS)
    ponderadores_data = dynamic_structure_data.get('ponderadores', [])
    if ponderadores_data:
        print(f"=== PROCESANDO PONDERADORES NUEVOS ===", file=sys.stderr)
        print(f"PONDERADORES DATA: {ponderadores_data}", file=sys.stderr)
        
        for pond_data in ponderadores_data:
            if isinstance(pond_data, dict) and pond_data.get('nombre'):
                try:
                    ponderador = Ponderador.objects.create(
                        proyecto=proyecto,
                        nombre=pond_data.get('nombre'),
                        tipo=pond_data.get('tipo', 'valorizacion'),
                        nivel_aplicacion=pond_data.get('nivel_aplicacion', 'proyecto'),
                        porcentaje=pond_data.get('porcentaje', 0),
                        monto_fijo=pond_data.get('monto_fijo', None),
                        descripcion=pond_data.get('descripcion', ''),
                        activo=True,
                        created_by_id=form_data.get('user_id'),
                        activated_by_id=form_data.get('user_id'),
                    )
                    print(f"NUEVO PONDERADOR CREADO: {ponderador.nombre} ({ponderador.tipo})", file=sys.stderr)
                except Exception as e:
                    print(f"ERROR CREANDO NUEVO PONDERADOR: {e}", file=sys.stderr)
    
    # 1.5. PROCESAR PONDERADORES EXISTENTES (ACTUALIZACIONES)
    existing_ponderadores_data = dynamic_structure_data.get('existing_ponderadores', [])
    if existing_ponderadores_data:
        print(f"=== PROCESANDO PONDERADORES EXISTENTES ===", file=sys.stderr)
        print(f"EXISTING PONDERADORES DATA: {existing_ponderadores_data}", file=sys.stderr)
        
        for pond_data in existing_ponderadores_data:
            if isinstance(pond_data, dict) and pond_data.get('id'):
                try:
                    ponderador_id = pond_data.get('id')
                    ponderador = Ponderador.objects.get(id=ponderador_id, proyecto=proyecto)
                    
                    # Actualizar campos
                    ponderador.nombre = pond_data.get('nombre', ponderador.nombre)
                    ponderador.tipo = pond_data.get('tipo', ponderador.tipo)
                    ponderador.porcentaje = pond_data.get('porcentaje', ponderador.porcentaje)
                    ponderador.monto_fijo = pond_data.get('monto_fijo', ponderador.monto_fijo)
                    ponderador.descripcion = pond_data.get('descripcion', ponderador.descripcion)
                    ponderador.activo = pond_data.get('activo', ponderador.activo)
                    
                    ponderador.save()
                    print(f"PONDERADOR EXISTENTE ACTUALIZADO: {ponderador.nombre} (ID: {ponderador_id}) - Activo: {ponderador.activo}", file=sys.stderr)
                except Ponderador.DoesNotExist:
                    print(f"PONDERADOR NO ENCONTRADO: ID {ponderador_id}", file=sys.stderr)
                except Exception as e:
                    print(f"ERROR ACTUALIZANDO PONDERADOR EXISTENTE: {e}", file=sys.stderr)
    
    # 2. CREAR FASES CON CONFIGURACIÓN DE COMERCIALIZACIÓN
    for fase_num, fase_info in fases_data.items():
        print(f"=== CREANDO FASE {fase_num} ===", file=sys.stderr)
        print(f"FASE_INFO: {fase_info}", file=sys.stderr)
        
        # Determinar si la fase es comercializable por defecto
        fase_comercializable = fase_info.get('comercializable', False)
        
        # Crear la fase
        fase = Fase.objects.create(
            proyecto=proyecto,
            nombre=fase_info.get('nombre', f"Fase {fase_num}"),
            descripcion=f"Fase {fase_num} del proyecto {proyecto.nombre}",
            numero_fase=fase_num,
            precio_m2=1000.00,
        )
        print(f"FASE CREADA: {fase.nombre} (ID: {fase.id})", file=sys.stderr)
        
        # Procesar ponderadores específicos de la fase
        fase_ponderadores = fase_info.get('ponderadores', [])
        if fase_ponderadores:
            print(f"  PROCESANDO PONDERADORES DE FASE: {fase_ponderadores}", file=sys.stderr)
            for pond_data in fase_ponderadores:
                if isinstance(pond_data, dict) and pond_data.get('nombre'):
                    try:
                        ponderador = Ponderador.objects.create(
                            proyecto=proyecto,
                            fase=fase,
                            nombre=pond_data.get('nombre'),
                            tipo=pond_data.get('tipo', 'valorizacion'),
                            nivel_aplicacion='fase',
                            porcentaje=pond_data.get('porcentaje', 0),
                            monto_fijo=pond_data.get('monto_fijo', None),
                            descripcion=pond_data.get('descripcion', ''),
                            activo=True,
                            created_by_id=form_data.get('user_id'),
                            activated_by_id=form_data.get('user_id'),
                        )
                        print(f"  PONDERADOR FASE CREADO: {ponderador.nombre}", file=sys.stderr)
                    except Exception as e:
                        print(f"  ERROR CREANDO PONDERADOR FASE: {e}", file=sys.stderr)
        
        # Crear torres si es proyecto de departamentos
        if proyecto.tipo == 'departamentos' and fase_info.get('torres'):
            torres = fase_info['torres']
            print(f"  TORRES DATA: {torres}", file=sys.stderr)
            print(f"  CREANDO {len(torres)} TORRES", file=sys.stderr)
            create_dynamic_apartments_structure(fase, torres, fase_comercializable)
        
        # Crear sectores si es proyecto de terrenos  
        elif proyecto.tipo == 'terrenos' and fase_info.get('sectores'):
            sectores = fase_info['sectores']
            print(f"  SECTORES DATA: {sectores}", file=sys.stderr)
            print(f"  CREANDO {len(sectores)} SECTORES", file=sys.stderr)
            create_dynamic_land_structure(fase, sectores, fase_comercializable)
    
    print(f"=== ESTRUCTURA COMPLETADA ===", file=sys.stderr)


def process_ponderadores_only(proyecto, dynamic_structure_data, user_id):
    """Procesar solo ponderadores sin afectar la estructura de fases"""
    import sys
    
    print(f"=== PROCESANDO SOLO PONDERADORES ===", file=sys.stderr)
    
    # 1. PROCESAR PONDERADORES NUEVOS
    ponderadores_data = dynamic_structure_data.get('ponderadores', [])
    if ponderadores_data:
        print(f"=== PROCESANDO PONDERADORES NUEVOS ===", file=sys.stderr)
        print(f"PONDERADORES DATA: {ponderadores_data}", file=sys.stderr)
        
        for pond_data in ponderadores_data:
            if isinstance(pond_data, dict) and pond_data.get('nombre'):
                try:
                    ponderador = Ponderador.objects.create(
                        proyecto=proyecto,
                        nombre=pond_data.get('nombre'),
                        tipo=pond_data.get('tipo', 'valorizacion'),
                        nivel_aplicacion=pond_data.get('nivel_aplicacion', 'proyecto'),
                        porcentaje=pond_data.get('porcentaje', 0),
                        monto_fijo=pond_data.get('monto_fijo', None),
                        descripcion=pond_data.get('descripcion', ''),
                        activo=True,
                        created_by_id=user_id,
                        activated_by_id=user_id,
                    )
                    print(f"*** NUEVO PONDERADOR CREADO EN DB: {ponderador.nombre} (ID: {ponderador.id}) ***", file=sys.stderr)
                    
                    # Verificar que se guardó en DB
                    ponderador_verificado = Ponderador.objects.get(id=ponderador.id)
                    print(f"*** VERIFICACIÓN DB: {ponderador_verificado.nombre} existe ***", file=sys.stderr)
                except Exception as e:
                    print(f"ERROR CREANDO NUEVO PONDERADOR: {e}", file=sys.stderr)
    
    # 1.5. PROCESAR PONDERADORES DE FASE (NUEVOS)
    ponderadores_fase_data = dynamic_structure_data.get('ponderadores_fase', [])
    if ponderadores_fase_data:
        print(f"=== PROCESANDO PONDERADORES DE FASE NUEVOS ===", file=sys.stderr)
        print(f"PONDERADORES FASE DATA: {ponderadores_fase_data}", file=sys.stderr)
        
        for pond_data in ponderadores_fase_data:
            if isinstance(pond_data, dict) and pond_data.get('nombre'):
                try:
                    # Obtener la fase correspondiente
                    fase_numero = pond_data.get('fase_numero')
                    fase = proyecto.fases.filter(numero_fase=fase_numero, activo=True).first()
                    
                    if fase:
                        print(f"*** CREANDO PONDERADOR DE FASE ***", file=sys.stderr)
                        print(f"*** PROYECTO: {proyecto.id} ({proyecto.nombre}) ***", file=sys.stderr)
                        print(f"*** FASE: {fase.id} ({fase.nombre}) ***", file=sys.stderr)
                        print(f"*** DATOS: {pond_data} ***", file=sys.stderr)
                        
                        ponderador = Ponderador.objects.create(
                            proyecto=proyecto,
                            fase=fase,
                            nombre=pond_data.get('nombre'),
                            tipo=pond_data.get('tipo', 'valorizacion'),
                            nivel_aplicacion='fase',
                            porcentaje=pond_data.get('porcentaje', 0),
                            monto_fijo=pond_data.get('monto_fijo', None),
                            descripcion=pond_data.get('descripcion', ''),
                            activo=True,
                            created_by_id=user_id,
                            activated_by_id=user_id,
                        )
                        print(f"*** NUEVO PONDERADOR DE FASE CREADO EN DB: ID={ponderador.id}, nombre='{ponderador.nombre}', nivel='{ponderador.nivel_aplicacion}', proyecto_id={ponderador.proyecto_id}, fase_id={ponderador.fase_id} ***", file=sys.stderr)
                        
                        # Verificar que se guardó en DB
                        ponderador_verificado = Ponderador.objects.get(id=ponderador.id)
                        print(f"*** VERIFICACIÓN DB FASE: {ponderador_verificado.nombre} - nivel: {ponderador_verificado.nivel_aplicacion} - fase: {ponderador_verificado.fase_id} ***", file=sys.stderr)
                    else:
                        print(f"*** FASE {fase_numero} NO ENCONTRADA PARA PONDERADOR {pond_data.get('nombre')} ***", file=sys.stderr)
                        # Listar fases disponibles para debug
                        fases_disponibles = proyecto.fases.filter(activo=True).values_list('numero_fase', 'nombre')
                        print(f"*** FASES DISPONIBLES: {list(fases_disponibles)} ***", file=sys.stderr)
                except Exception as e:
                    print(f"ERROR CREANDO PONDERADOR DE FASE: {e}", file=sys.stderr)
    
    # 2. PROCESAR PONDERADORES EXISTENTES
    existing_ponderadores_data = dynamic_structure_data.get('existing_ponderadores', [])
    if existing_ponderadores_data:
        print(f"=== PROCESANDO PONDERADORES EXISTENTES ===", file=sys.stderr)
        print(f"EXISTING PONDERADORES DATA: {existing_ponderadores_data}", file=sys.stderr)
        
        for pond_data in existing_ponderadores_data:
            if isinstance(pond_data, dict) and pond_data.get('id'):
                try:
                    ponderador_id = pond_data.get('id')
                    ponderador = Ponderador.objects.get(id=ponderador_id, proyecto=proyecto)
                    
                    # Actualizar campos
                    ponderador.nombre = pond_data.get('nombre', ponderador.nombre)
                    ponderador.tipo = pond_data.get('tipo', ponderador.tipo)
                    ponderador.porcentaje = pond_data.get('porcentaje', ponderador.porcentaje)
                    ponderador.monto_fijo = pond_data.get('monto_fijo', ponderador.monto_fijo)
                    ponderador.descripcion = pond_data.get('descripcion', ponderador.descripcion)
                    ponderador.activo = pond_data.get('activo', ponderador.activo)
                    
                    ponderador.save()
                    print(f"PONDERADOR EXISTENTE ACTUALIZADO: {ponderador.nombre} (ID: {ponderador_id}) - Activo: {ponderador.activo}", file=sys.stderr)
                except Ponderador.DoesNotExist:
                    print(f"PONDERADOR NO ENCONTRADO: ID {ponderador_id}", file=sys.stderr)
                except Exception as e:
                    print(f"ERROR ACTUALIZANDO PONDERADOR EXISTENTE: {e}", file=sys.stderr)


def process_comercializacion_only(proyecto, dynamic_structure_data):
    """Procesar solo la comercialización de fases sin afectar la estructura"""
    import sys
    
    print(f"=== PROCESANDO SOLO COMERCIALIZACIÓN ===", file=sys.stderr)
    
    fases_data = dynamic_structure_data.get('fases', {})
    for fase_num, fase_info in fases_data.items():
        try:
            # Buscar la fase existente
            fase = proyecto.fases.filter(numero_fase=fase_num, activo=True).first()
            if not fase:
                print(f"*** FASE {fase_num} NO ENCONTRADA ***", file=sys.stderr)
                continue
                
            comercializable = fase_info.get('comercializable', False)
            print(f"*** FASE {fase_num}: comercializable = {comercializable} ***", file=sys.stderr)
            
            # Actualizar todos los inmuebles de la fase
            if comercializable:
                # Marcar todos los inmuebles como comercializables
                count = fase.inmuebles.update(disponible_comercializacion=True)
                print(f"*** MARCADOS {count} INMUEBLES COMO COMERCIALIZABLES EN FASE {fase_num} ***", file=sys.stderr)
            else:
                # Marcar todos los inmuebles como NO comercializables
                count = fase.inmuebles.update(disponible_comercializacion=False)
                print(f"*** MARCADOS {count} INMUEBLES COMO NO COMERCIALIZABLES EN FASE {fase_num} ***", file=sys.stderr)
                
        except Exception as e:
            print(f"ERROR PROCESANDO COMERCIALIZACIÓN DE FASE {fase_num}: {e}", file=sys.stderr)


def _build_existing_structure_data(proyecto):
    """Construir datos de estructura existente para pre-cargar en el formulario de edición"""
    import sys
    
    print(f"=== CONSTRUYENDO ESTRUCTURA EXISTENTE ===", file=sys.stderr)
    print(f"PROYECTO: {proyecto.nombre}", file=sys.stderr)
    
    structure_data = {
        'fases': {},
        'ponderadores': []
    }
    
    # 1. OBTENER PONDERADORES DEL PROYECTO
    ponderadores_proyecto = proyecto.ponderadores.filter(activo=True, nivel_aplicacion='proyecto')
    for ponderador in ponderadores_proyecto:
        structure_data['ponderadores'].append({
            'id': ponderador.id,
            'nombre': ponderador.nombre,
            'tipo': ponderador.tipo,
            'porcentaje': float(ponderador.porcentaje) if ponderador.porcentaje else 0,
            'monto_fijo': float(ponderador.monto_fijo) if ponderador.monto_fijo else None,
            'descripcion': ponderador.descripcion,
            'nivel_aplicacion': ponderador.nivel_aplicacion
        })
        print(f"  PONDERADOR: {ponderador.nombre} ({ponderador.tipo})", file=sys.stderr)
    
    # 2. OBTENER ESTRUCTURA DE FASES
    fases = proyecto.fases.filter(activo=True).order_by('numero_fase')
    for fase in fases:
        # Verificar si la fase es comercializable
        inmuebles_comercializables = fase.inmuebles.filter(disponible_comercializacion=True).count()
        es_comercializable = inmuebles_comercializables > 0
        
        fase_data = {
            'id': fase.id,
            'nombre': fase.nombre,
            'numero_fase': fase.numero_fase,
            'comercializable': es_comercializable,
            'torres': {},
            'sectores': {},
            'ponderadores': []
        }
        
        # Ponderadores de la fase
        ponderadores_fase = fase.ponderadores.filter(activo=True)
        for ponderador in ponderadores_fase:
            fase_data['ponderadores'].append({
                'id': ponderador.id,
                'nombre': ponderador.nombre,
                'tipo': ponderador.tipo,
                'porcentaje': float(ponderador.porcentaje) if ponderador.porcentaje else 0,
                'monto_fijo': float(ponderador.monto_fijo) if ponderador.monto_fijo else None,
                'descripcion': ponderador.descripcion,
                'nivel_aplicacion': ponderador.nivel_aplicacion
            })
        
        # Estructura de torres (para departamentos)
        if proyecto.tipo == 'departamentos':
            torres = fase.torres.filter(activo=True).order_by('numero_torre')
            for torre in torres:
                # Verificar si la torre es comercializable (a través de los pisos)
                inmuebles_comercializables = 0
                for piso in torre.pisos.filter(activo=True):
                    inmuebles_comercializables += piso.inmuebles.filter(disponible_comercializacion=True).count()
                es_comercializable = inmuebles_comercializables > 0
                
                torre_data = {
                    'id': torre.id,
                    'nombre': torre.nombre,
                    'numero_torre': torre.numero_torre,
                    'comercializable': es_comercializable,
                    'pisos': {}
                }
                
                # Obtener pisos y departamentos
                pisos = torre.pisos.filter(activo=True).order_by('numero_piso')
                for piso in pisos:
                    departamentos_count = piso.inmuebles.filter(disponible=True).count()
                    torre_data['pisos'][piso.numero_piso] = departamentos_count
                
                fase_data['torres'][torre.numero_torre] = torre_data
                print(f"  TORRE: {torre.nombre} - {len(torre_data['pisos'])} pisos", file=sys.stderr)
        
        # Estructura de sectores (para terrenos)
        elif proyecto.tipo == 'terrenos':
            sectores = fase.sectores.filter(activo=True).order_by('numero_sector')
            for sector in sectores:
                # Verificar si el sector es comercializable (a través de las manzanas)
                inmuebles_comercializables = 0
                for manzana in sector.manzanas.filter(activo=True):
                    inmuebles_comercializables += manzana.inmuebles.filter(disponible_comercializacion=True).count()
                es_comercializable = inmuebles_comercializables > 0
                
                sector_data = {
                    'id': sector.id,
                    'nombre': sector.nombre,
                    'numero_sector': sector.numero_sector,
                    'comercializable': es_comercializable,
                    'manzanas': {}
                }
                
                # Obtener manzanas y terrenos
                manzanas = sector.manzanas.filter(activo=True).order_by('numero_manzana')
                for manzana in manzanas:
                    terrenos_count = manzana.inmuebles.filter(disponible=True).count()
                    sector_data['manzanas'][manzana.numero_manzana] = terrenos_count
                
                fase_data['sectores'][sector.numero_sector] = sector_data
                print(f"  SECTOR: {sector.nombre} - {len(sector_data['manzanas'])} manzanas", file=sys.stderr)
        
        structure_data['fases'][fase.numero_fase] = fase_data
        print(f"FASE: {fase.nombre} - comercializable: {fase.es_comercializable}", file=sys.stderr)
    
    print(f"ESTRUCTURA EXISTENTE: {len(structure_data['fases'])} fases, {len(structure_data['ponderadores'])} ponderadores", file=sys.stderr)
    return structure_data


def create_apartments_structure(fase, fase_data):
    """Crea la estructura para proyectos de departamentos"""
    numero_torres = fase_data.get('torres', 1)
    pisos_inicio = fase_data.get('pisos_inicio', 1)
    pisos_fin = fase_data.get('pisos_fin', 10)
    departamentos_por_piso = fase_data.get('deptos_piso', 4)
    
    for torre_num in range(1, numero_torres + 1):
        # Crear la torre
        torre = Torre.objects.create(
            fase=fase,
            nombre=f"Torre {torre_num}",
            numero_torre=torre_num,
            numero_pisos=pisos_fin - pisos_inicio + 1,
            descripcion=f"Torre {torre_num} de la {fase.nombre}"
        )
        
        for piso_num in range(pisos_inicio, pisos_fin + 1):
            # Crear el piso
            piso = Piso.objects.create(
                torre=torre,
                numero_piso=piso_num,
                nombre=f"Piso {piso_num}",
                descripcion=f"Piso {piso_num} de la Torre {torre_num}"
            )
            
            # Crear los departamentos
            for depto_num in range(1, departamentos_por_piso + 1):
                codigo = f"T{torre_num:02d}P{piso_num:02d}D{depto_num:02d}"
                
                Inmueble.objects.create(
                    fase=fase,
                    piso=piso,
                    codigo=codigo,
                    tipo='departamento',
                    m2=85.0,  # Área por defecto
                    estado='disponible',
                    disponible=True,
                    caracteristicas=f"Departamento {codigo} en Torre {torre_num}, Piso {piso_num}"
                )


def create_land_structure(fase, fase_data):
    """Crea la estructura para proyectos de terrenos"""
    numero_sectores = fase_data.get('sectores', 1)
    manzanas_inicio = fase_data.get('manzanas_inicio', 1)
    manzanas_fin = fase_data.get('manzanas_fin', 10)
    terrenos_por_manzana = fase_data.get('terrenos_manzana', 8)
    
    for sector_num in range(1, numero_sectores + 1):
        # Crear el sector
        sector = Sector.objects.create(
            fase=fase,
            nombre=f"Sector {sector_num}",
            numero_sector=sector_num,
            descripcion=f"Sector {sector_num} de la {fase.nombre}"
        )
        
        for manzana_num in range(manzanas_inicio, manzanas_fin + 1):
            # Crear la manzana
            manzana = Manzana.objects.create(
                sector=sector,
                numero_manzana=manzana_num,
                nombre=f"Manzana {manzana_num}",
                descripcion=f"Manzana {manzana_num} del Sector {sector_num}"
            )
            
            # Crear los terrenos
            for terreno_num in range(1, terrenos_por_manzana + 1):
                codigo = f"S{sector_num:02d}M{manzana_num:02d}T{terreno_num:02d}"
                
                Inmueble.objects.create(
                    fase=fase,
                    manzana=manzana,
                    codigo=codigo,
                    tipo='terreno',
                    m2=450.0,  # Área por defecto
                    estado='disponible',
                    disponible=True,
                    caracteristicas=f"Terreno {codigo} en Sector {sector_num}, Manzana {manzana_num}"
                )


def create_dynamic_apartments_structure(fase, torres_data, fase_comercializable=False):
    """Crea la estructura para proyectos de departamentos con datos dinámicos REALES"""
    import sys
    print(f"=== CREANDO DEPARTAMENTOS DINÁMICOS ===", file=sys.stderr)
    print(f"Fase: {fase.nombre}", file=sys.stderr)
    print(f"Torres data: {torres_data}", file=sys.stderr)
    
    for torre_num, torre_info in torres_data.items():
        print(f"PROCESANDO TORRE {torre_num}: {torre_info}", file=sys.stderr)
        
        # Validar que torre_info sea un diccionario
        if not isinstance(torre_info, dict):
            print(f"ERROR: Torre {torre_num} no es diccionario", file=sys.stderr)
            continue
        
        # Obtener datos de la torre
        pisos_data = torre_info.get('pisos', {})
        if not pisos_data:
            # Usar datos básicos si no hay pisos específicos
            pisos_inicio = torre_info.get('pisos_inicio', 1)
            pisos_fin = torre_info.get('pisos_fin', 1)
            deptos_piso = torre_info.get('deptos_piso', 2)
            pisos_data = {piso: deptos_piso for piso in range(pisos_inicio, pisos_fin + 1)}
        
        print(f"TORRE {torre_num} - Pisos data: {pisos_data}", file=sys.stderr)
        
        # Crear la torre
        torre = Torre.objects.create(
            fase=fase,
            nombre=torre_info.get('nombre', f"Torre {torre_num}"),
            numero_torre=int(torre_num),
            numero_pisos=len(pisos_data),
            descripcion=f"Torre {torre_num} de la {fase.nombre}"
        )
        
        departamentos_creados = 0
        
        # Crear cada piso con sus departamentos específicos
        for piso_num, departamentos_count in pisos_data.items():
            print(f"CREANDO PISO {piso_num} con {departamentos_count} departamentos", file=sys.stderr)
            
            # Crear el piso
            piso = Piso.objects.create(
                torre=torre,
                numero_piso=int(piso_num),
                nombre=f"Piso {piso_num}",
                descripcion=f"Piso {piso_num} de la Torre {torre_num}"
            )
            
            # Crear los departamentos específicos de este piso
            for depto_num in range(1, int(departamentos_count) + 1):
                codigo = f"T{int(torre_num):02d}P{int(piso_num):02d}D{depto_num:02d}"
                
                Inmueble.objects.create(
                    fase=fase,
                    piso=piso,
                    codigo=codigo,
                    tipo='departamento',
                    m2=85.0,
                    estado='disponible',
                    disponible=True,
                    disponible_comercializacion=fase_comercializable,
                    caracteristicas=f"Departamento {codigo} en Torre {torre_num}, Piso {piso_num}"
                )
                departamentos_creados += 1
                print(f"  CREADO: {codigo}", file=sys.stderr)
        
        print(f"TORRE {torre_num} COMPLETADA: {departamentos_creados} departamentos", file=sys.stderr)
    
    print(f"=== ESTRUCTURA DEPARTAMENTOS COMPLETADA ===", file=sys.stderr)


def create_dynamic_land_structure(fase, sectores_data, fase_comercializable=False):
    """Crea la estructura para proyectos de terrenos con datos dinámicos"""
    print(f"DEBUG: Creando estructura de terrenos para fase {fase.nombre}")
    print(f"DEBUG: Sectores data completo: {sectores_data}")
    print(f"DEBUG: Tipo de sectores_data: {type(sectores_data)}")
    
    for sector_num, sector_info in sectores_data.items():
        print(f"DEBUG: Procesando Sector {sector_num} (tipo: {type(sector_num)})")
        print(f"DEBUG: Sector info: {sector_info}")
        print(f"DEBUG: Tipo de sector_info: {type(sector_info)}")
        
        # Validar que sector_info sea un diccionario
        if not isinstance(sector_info, dict):
            print(f"ERROR: Sector {sector_num} - sector_info no es un diccionario: {sector_info}")
            continue
            
        # Determinar comercialización del sector
        sector_comercializable = sector_info.get('comercializable', False)
        inmuebles_comercializables = fase_comercializable or sector_comercializable
        
        # Obtener y validar datos de configuración
        manzanas_inicio = sector_info.get('manzanas_inicio', 1)
        manzanas_fin = sector_info.get('manzanas_fin', 10)
        terrenos_por_manzana = sector_info.get('terrenos_manzana', 8)
        
        # Asegurar que sean enteros
        try:
            manzanas_inicio = int(manzanas_inicio)
            manzanas_fin = int(manzanas_fin)
            terrenos_por_manzana = int(terrenos_por_manzana)
            sector_num_int = int(sector_num)
        except (ValueError, TypeError) as e:
            print(f"ERROR: Sector {sector_num} - Error convirtiendo a entero: {e}")
            print(f"  manzanas_inicio: {manzanas_inicio} (tipo: {type(manzanas_inicio)})")
            print(f"  manzanas_fin: {manzanas_fin} (tipo: {type(manzanas_fin)})")
            print(f"  terrenos_por_manzana: {terrenos_por_manzana} (tipo: {type(terrenos_por_manzana)})")
            continue
        
        # Validar rangos lógicos
        if manzanas_inicio > manzanas_fin:
            print(f"ERROR: Sector {sector_num} - Manzana inicio ({manzanas_inicio}) mayor que manzana fin ({manzanas_fin})")
            continue
            
        if terrenos_por_manzana <= 0:
            print(f"ERROR: Sector {sector_num} - Terrenos por manzana debe ser mayor a 0: {terrenos_por_manzana}")
            continue
        
        # Calcular total esperado
        total_manzanas = manzanas_fin - manzanas_inicio + 1
        total_terrenos_esperados = total_manzanas * terrenos_por_manzana
        
        print(f"DEBUG: Sector {sector_num} - Manzanas: {manzanas_inicio} a {manzanas_fin} (total: {total_manzanas} manzanas)")
        print(f"DEBUG: Sector {sector_num} - Terrenos por manzana: {terrenos_por_manzana}")
        print(f"DEBUG: Sector {sector_num} - Total terrenos esperados: {total_terrenos_esperados}")
        
        # Crear el sector
        sector = Sector.objects.create(
            fase=fase,
            nombre=sector_info.get('nombre', f"Sector {sector_num}"),
            numero_sector=sector_num_int,
            descripcion=f"{sector_info.get('nombre', f'Sector {sector_num}')} de la {fase.nombre}"
        )
        
        terrenos_creados = 0
        manzanas_creadas = 0
        
        # Crear exactamente las manzanas solicitadas
        for manzana_num in range(manzanas_inicio, manzanas_fin + 1):
            print(f"DEBUG: Sector {sector_num} - Creando manzana {manzana_num}")
            
            # Crear la manzana
            manzana = Manzana.objects.create(
                sector=sector,
                numero_manzana=manzana_num,
                nombre=f"Manzana {manzana_num}",
                descripcion=f"Manzana {manzana_num} del {sector.nombre}"
            )
            manzanas_creadas += 1
            
            # Crear exactamente los terrenos solicitados por manzana
            for terreno_num in range(1, terrenos_por_manzana + 1):
                codigo = f"S{sector_num_int:02d}M{manzana_num:02d}T{terreno_num:02d}"
                
                print(f"DEBUG: Sector {sector_num} - Creando terreno {codigo}")
                
                Inmueble.objects.create(
                    fase=fase,
                    manzana=manzana,
                    codigo=codigo,
                    tipo='terreno',
                    m2=450.0,  # Área por defecto
                    estado='disponible',
                    disponible=True,
                    disponible_comercializacion=inmuebles_comercializables,
                    caracteristicas=f"Terreno {codigo} en {sector.nombre}, Manzana {manzana_num}"
                )
                terrenos_creados += 1
        
        print(f"DEBUG: Sector {sector_num} - RESUMEN:")
        print(f"  Manzanas creadas: {manzanas_creadas} (esperadas: {total_manzanas})")
        print(f"  Terrenos creados: {terrenos_creados} (esperados: {total_terrenos_esperados})")
        
        # Verificar que las cantidades coincidan
        if manzanas_creadas != total_manzanas:
            print(f"ERROR: Sector {sector_num} - Manzanas creadas ({manzanas_creadas}) != esperadas ({total_manzanas})")
            
        if terrenos_creados != total_terrenos_esperados:
            print(f"ERROR: Sector {sector_num} - Terrenos creados ({terrenos_creados}) != esperados ({total_terrenos_esperados})")
            
    print(f"DEBUG: Estructura de terrenos completada para fase {fase.nombre}")


def count_total_properties(form_data):
    """Calcula el total de inmuebles que se crearán con estructura dinámica"""
    dynamic_structure_data = form_data.get('dynamic_structure_data', {})
    fases_data = dynamic_structure_data.get('fases', {})
    tipo_proyecto = form_data.get('tipo')
    
    total_inmuebles = 0
    
    print(f"DEBUG COUNT: Tipo proyecto: {tipo_proyecto}")
    print(f"DEBUG COUNT: Fases data: {fases_data}")
    
    for fase_num, fase_info in fases_data.items():
        if tipo_proyecto == 'departamentos' and fase_info.get('torres'):
            print(f"DEBUG COUNT: Fase {fase_num} - Torres: {fase_info['torres']}")
            for torre_num, torre_info in fase_info['torres'].items():
                pisos_inicio = torre_info.get('pisos_inicio', 1)
                pisos_fin = torre_info.get('pisos_fin', 10)
                departamentos_por_piso = torre_info.get('deptos_piso', 4)
                
                # Usar la misma lógica que create_dynamic_apartments_structure
                departamentos_torre = 0
                for piso_num in range(pisos_inicio, pisos_fin + 1):
                    departamentos_torre += departamentos_por_piso
                
                total_inmuebles += departamentos_torre
                
                print(f"DEBUG COUNT: Torre {torre_num} - Pisos: {pisos_inicio} a {pisos_fin}")
                print(f"DEBUG COUNT: Torre {torre_num} - Departamentos/piso: {departamentos_por_piso}")
                print(f"DEBUG COUNT: Torre {torre_num} - Total calculado: {departamentos_torre}")
                print(f"DEBUG COUNT: Total acumulado: {total_inmuebles}")
                
        elif tipo_proyecto == 'terrenos' and fase_info.get('sectores'):
            for sector_num, sector_info in fase_info['sectores'].items():
                manzanas_inicio = sector_info.get('manzanas_inicio', 1)
                manzanas_fin = sector_info.get('manzanas_fin', 10)
                terrenos_por_manzana = sector_info.get('terrenos_manzana', 8)
                
                # Usar la misma lógica que create_dynamic_land_structure
                terrenos_sector = 0
                for manzana_num in range(manzanas_inicio, manzanas_fin + 1):
                    terrenos_sector += terrenos_por_manzana
                
                total_inmuebles += terrenos_sector
    
    return total_inmuebles


def update_project_structure(proyecto, form_data, user_id):
    """Actualiza la estructura del proyecto en modo edición - permite regeneración completa"""
    dynamic_structure_data = form_data.get('dynamic_structure_data', {})
    
    # Si se proporcionó nueva estructura, regenerar completamente
    if dynamic_structure_data.get('fases'):
        # Para simplificar en el edit, regenerar toda la estructura
        # (En el futuro se podría hacer más granular)
        
        # Eliminar estructura existente (cuidadosamente)
        # Solo eliminar si no hay inmuebles vendidos
        fases_existentes = proyecto.fases.all()
        for fase in fases_existentes:
            if fase.inmuebles_vendidos == 0:
                # Es seguro eliminar esta fase
                fase.delete()
            else:
                # No eliminar fases con ventas - mantener estructura existente
                continue
        
        # Preparar datos para create_project_structure incluyendo user_id
        form_data_with_user = form_data.copy()
        form_data_with_user['user_id'] = user_id
        
        # Crear nueva estructura
        create_project_structure(proyecto, form_data_with_user)


# ============================================================
# PONDERADORES DE PRECIO
# ============================================================

@login_required
def ponderadores_list(request, proyecto_pk):
    """Lista de ponderadores de un proyecto"""
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk, activo=True)
    
    # Obtener ponderadores activos del proyecto
    ponderadores = proyecto.ponderadores.filter(activo=True).order_by(
        'nivel_aplicacion', 'tipo', 'nombre'
    )
    
    # Filtros
    nivel_filter = request.GET.get('nivel', '')
    tipo_filter = request.GET.get('tipo', '')
    activo_filter = request.GET.get('activo', '')
    
    if nivel_filter:
        ponderadores = ponderadores.filter(nivel_aplicacion=nivel_filter)
    
    if tipo_filter:
        ponderadores = ponderadores.filter(tipo=tipo_filter)
    
    if activo_filter == 'true':
        ponderadores = ponderadores.filter(activo=True)
    elif activo_filter == 'false':
        ponderadores = ponderadores.filter(activo=False)
    
    # Paginación
    paginator = Paginator(ponderadores, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'real_estate_projects/ponderadores/list.html', {
        'title': f'Ponderadores - {proyecto.nombre}',
        'proyecto': proyecto,
        'page_obj': page_obj,
        'niveles_aplicacion': Ponderador.NIVELES_APLICACION,
        'tipos_ponderador': Ponderador.TIPOS_PONDERADOR,
        'filters': {
            'nivel': nivel_filter,
            'tipo': tipo_filter,
            'activo': activo_filter,
        }
    })


@login_required
def ponderador_create(request, proyecto_pk):
    """Crear ponderador para un proyecto"""
    from .forms import PonderadorForm
    from django.db import transaction
    
    proyecto = get_object_or_404(Proyecto, pk=proyecto_pk, activo=True)
    
    if request.method == 'POST':
        form = PonderadorForm(request.POST, proyecto=proyecto, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    ponderador = form.save()
                    messages.success(request, f'Ponderador "{ponderador.nombre}" creado exitosamente.')
                    return redirect('projects:ponderadores_list', proyecto_pk=proyecto.pk)
            except Exception as e:
                messages.error(request, f'Error al crear el ponderador: {str(e)}')
    else:
        form = PonderadorForm(proyecto=proyecto, user=request.user)
    
    return render(request, 'real_estate_projects/ponderadores/form.html', {
        'title': f'Crear Ponderador - {proyecto.nombre}',
        'form': form,
        'proyecto': proyecto,
        'is_create': True,
    })


@login_required
def ponderador_edit(request, pk):
    """Editar ponderador"""
    from .forms import PonderadorForm
    from django.db import transaction
    
    ponderador = get_object_or_404(Ponderador, pk=pk, activo=True)
    proyecto = ponderador.proyecto
    
    if request.method == 'POST':
        form = PonderadorForm(request.POST, instance=ponderador, proyecto=proyecto, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    ponderador = form.save()
                    messages.success(request, f'Ponderador "{ponderador.nombre}" actualizado exitosamente.')
                    return redirect('projects:ponderadores_list', proyecto_pk=proyecto.pk)
            except Exception as e:
                messages.error(request, f'Error al actualizar el ponderador: {str(e)}')
    else:
        form = PonderadorForm(instance=ponderador, proyecto=proyecto, user=request.user)
    
    return render(request, 'real_estate_projects/ponderadores/form.html', {
        'title': f'Editar Ponderador: {ponderador.nombre}',
        'form': form,
        'proyecto': proyecto,
        'ponderador': ponderador,
        'is_create': False,
    })


@login_required
def ponderador_detail(request, pk):
    """Detalle de ponderador"""
    ponderador = get_object_or_404(Ponderador, pk=pk)
    proyecto = ponderador.proyecto
    
    # Obtener versiones históricas si existen
    versiones_anteriores = Ponderador.objects.filter(
        ponderador_padre=ponderador
    ).order_by('-created_at')
    
    versiones_hijo = ponderador.versiones_hijo.all().order_by('-created_at')
    
    return render(request, 'real_estate_projects/ponderadores/detail.html', {
        'title': f'Ponderador: {ponderador.nombre}',
        'ponderador': ponderador,
        'proyecto': proyecto,
        'versiones_anteriores': versiones_anteriores,
        'versiones_hijo': versiones_hijo,
    })


@login_required
def ponderador_activate(request, pk):
    """Activar ponderador"""
    ponderador = get_object_or_404(Ponderador, pk=pk)
    
    if request.method == 'POST':
        try:
            ponderador.activar(request.user)
            messages.success(request, f'Ponderador "{ponderador.nombre}" activado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al activar el ponderador: {str(e)}')
    
    return redirect('projects:ponderador_detail', pk=ponderador.pk)


@login_required
def ponderador_deactivate(request, pk):
    """Desactivar ponderador"""
    ponderador = get_object_or_404(Ponderador, pk=pk)
    
    if request.method == 'POST':
        try:
            ponderador.desactivar(request.user)
            messages.success(request, f'Ponderador "{ponderador.nombre}" desactivado exitosamente.')
        except Exception as e:
            messages.error(request, f'Error al desactivar el ponderador: {str(e)}')
    
    return redirect('projects:ponderador_detail', pk=ponderador.pk)


@login_required
def fase_comercializacion(request, fase_pk):
    """Gestionar comercialización en cascada de una fase"""
    from .forms import ComercializacionFaseForm
    from django.db import transaction
    
    fase = get_object_or_404(Fase, pk=fase_pk, activo=True)
    
    if request.method == 'POST':
        form = ComercializacionFaseForm(request.POST, fase=fase)
        if form.is_valid():
            try:
                with transaction.atomic():
                    actualizado = form.save()
                    estado = "comercializables" if form.cleaned_data.get('comercializable') else "no comercializables"
                    messages.success(request, f'Se marcaron {actualizado} inmuebles como {estado} en la fase "{fase.nombre}".')
                    
                    # Si se marcó la fase como comercializable, marcar también todas las torres/sectores
                    if form.cleaned_data.get('comercializable'):
                        if fase.proyecto.tipo == 'departamentos':
                            for torre in fase.torres.all():
                                torre.marcar_comercializable(True)
                        elif fase.proyecto.tipo == 'terrenos':
                            for sector in fase.sectores.all():
                                sector.marcar_comercializable(True)
                        
                        messages.info(request, 'También se marcaron automáticamente todas las torres/sectores de esta fase como comercializables.')
                    
                    return redirect('projects:detail', pk=fase.proyecto.pk)
            except Exception as e:
                messages.error(request, f'Error al actualizar la comercialización: {str(e)}')
    else:
        form = ComercializacionFaseForm(fase=fase)
    
    return render(request, 'real_estate_projects/comercializacion/fase_form.html', {
        'title': f'Comercialización - {fase.nombre}',
        'form': form,
        'fase': fase,
        'proyecto': fase.proyecto,
    })


@login_required
def torre_comercializacion(request, torre_pk):
    """Gestionar comercialización de una torre"""
    from .forms import ComercializacionTorreForm
    from django.db import transaction
    
    torre = get_object_or_404(Torre, pk=torre_pk, activo=True)
    
    if request.method == 'POST':
        form = ComercializacionTorreForm(request.POST, torre=torre)
        if form.is_valid():
            try:
                with transaction.atomic():
                    actualizado = form.save()
                    estado = "comercializables" if form.cleaned_data.get('comercializable') else "no comercializables"
                    messages.success(request, f'Se marcaron {actualizado} inmuebles como {estado} en la torre "{torre.nombre}".')
                    return redirect('projects:detail', pk=torre.fase.proyecto.pk)
            except Exception as e:
                messages.error(request, f'Error al actualizar la comercialización: {str(e)}')
    else:
        form = ComercializacionTorreForm(torre=torre)
    
    return render(request, 'real_estate_projects/comercializacion/torre_form.html', {
        'title': f'Comercialización - {torre.nombre}',
        'form': form,
        'torre': torre,
        'fase': torre.fase,
        'proyecto': torre.fase.proyecto,
    })


@login_required
def sector_comercializacion(request, sector_pk):
    """Gestionar comercialización de un sector"""
    from .forms import ComercializacionSectorForm
    from django.db import transaction
    
    sector = get_object_or_404(Sector, pk=sector_pk, activo=True)
    
    if request.method == 'POST':
        form = ComercializacionSectorForm(request.POST, sector=sector)
        if form.is_valid():
            try:
                with transaction.atomic():
                    actualizado = form.save()
                    estado = "comercializables" if form.cleaned_data.get('comercializable') else "no comercializables"
                    messages.success(request, f'Se marcaron {actualizado} inmuebles como {estado} en el sector "{sector.nombre}".')
                    return redirect('projects:detail', pk=sector.fase.proyecto.pk)
            except Exception as e:
                messages.error(request, f'Error al actualizar la comercialización: {str(e)}')
    else:
        form = ComercializacionSectorForm(sector=sector)
    
    return render(request, 'real_estate_projects/comercializacion/sector_form.html', {
        'title': f'Comercialización - {sector.nombre}',
        'form': form,
        'sector': sector,
        'fase': sector.fase,
        'proyecto': sector.fase.proyecto,
    })


@login_required
def ajax_create_ponderador(request):
    """Vista AJAX para crear ponderadores desde el formulario de inmuebles"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener datos del formulario
        nombre = request.POST.get('nombre', '').strip()
        tipo = request.POST.get('tipo', 'valorizacion')
        nivel_aplicacion = request.POST.get('nivel_aplicacion', 'proyecto')
        porcentaje = request.POST.get('porcentaje', '0')
        descripcion = request.POST.get('descripcion', '').strip()
        proyecto_id = request.POST.get('proyecto_id')
        fase_id = request.POST.get('fase_id')
        
        # Validaciones básicas
        if not nombre:
            return JsonResponse({'success': False, 'error': 'El nombre es requerido'})
        
        if not proyecto_id:
            return JsonResponse({'success': False, 'error': 'Se requiere un proyecto'})
        
        try:
            porcentaje = float(porcentaje)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'El porcentaje debe ser un número válido'})
        
        # Obtener proyecto
        try:
            proyecto = Proyecto.objects.get(pk=proyecto_id, activo=True)
        except Proyecto.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Proyecto no encontrado'})
        
        # Obtener fase si es necesario
        fase = None
        if nivel_aplicacion == 'fase' and fase_id:
            try:
                fase = Fase.objects.get(pk=fase_id, proyecto=proyecto, activo=True)
            except Fase.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Fase no encontrada'})
        
        # Crear el ponderador
        ponderador = Ponderador.objects.create(
            nombre=nombre,
            tipo=tipo,
            nivel_aplicacion=nivel_aplicacion,
            porcentaje=porcentaje,
            descripcion=descripcion,
            proyecto=proyecto,
            fase=fase,
            created_by=request.user,
            activated_by=request.user,
            activo=True
        )
        
        return JsonResponse({
            'success': True,
            'ponderador': {
                'id': ponderador.pk,
                'nombre': ponderador.nombre,
                'porcentaje': float(ponderador.porcentaje),
                'tipo_display': ponderador.get_tipo_display(),
                'nivel_display': ponderador.get_nivel_aplicacion_display()
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error interno: {str(e)}'})
