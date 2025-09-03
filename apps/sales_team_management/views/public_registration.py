# apps/sales_team_management/views/public_registration.py
"""
Vista pública de auto-registro para usuarios sin necesidad de login
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
import json

from ..models import OrganizationalUnit, PositionType, TeamMembership

User = get_user_model()


@ensure_csrf_cookie
def public_register_form(request, unit_code):
    """Vista pública del formulario de auto-registro"""
    
    # Verificar que la unidad existe y tiene registro público habilitado
    unit = get_object_or_404(
        OrganizationalUnit, 
        code=unit_code, 
        is_active=True, 
        public_registration_enabled=True
    )
    
    # Obtener posiciones disponibles para esta unidad (excluyendo gerentes/jefes)
    available_positions = PositionType.objects.filter(
        hierarchy_level__gte=3,  # Solo Team Leader (3) y Vendedor (4)
        is_active=True
    ).filter(
        applicable_unit_types__contains=unit.unit_type
    ).order_by('hierarchy_level')
    
    context = {
        'unit': unit,
        'available_positions': available_positions
    }
    
    return render(request, 'sales_team_management/public/register.html', context)


@csrf_exempt
def public_register_submit(request):
    """Procesar el formulario de auto-registro público"""
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        # Obtener datos del formulario
        unit_code = request.POST.get('unit_code')
        first_name = request.POST.get('first_name', '').strip().title()  # Title Case
        last_name = request.POST.get('last_name', '').strip().title()    # Title Case
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Campos adicionales
        cedula = request.POST.get('cedula', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        fecha_nacimiento = request.POST.get('fecha_nacimiento', '').strip()
        domicilio = request.POST.get('domicilio', '').strip()
        latitud = request.POST.get('latitud', '').strip()
        longitud = request.POST.get('longitud', '').strip()
        foto_perfil = request.FILES.get('foto_perfil')
        
        # Verificar que la unidad existe y tiene registro público habilitado
        unit = get_object_or_404(
            OrganizationalUnit, 
            code=unit_code, 
            is_active=True, 
            public_registration_enabled=True
        )
        
        # Generar username automáticamente: primera letra del nombre + primer apellido
        def generate_username(first_name, last_name):
            # Obtener primera letra del primer nombre
            first_letter = first_name.split()[0][0].lower() if first_name else ''
            # Obtener primer apellido (primera palabra del campo last_name)
            first_surname = last_name.split()[0].lower() if last_name else ''
            # Limpiar caracteres especiales y acentos
            import unicodedata
            first_letter = unicodedata.normalize('NFD', first_letter).encode('ascii', 'ignore').decode('ascii')
            first_surname = unicodedata.normalize('NFD', first_surname).encode('ascii', 'ignore').decode('ascii')
            
            base_username = f"{first_letter}{first_surname}"
            
            # Asegurar unicidad agregando número si es necesario
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            return username
        
        # Generar username
        generated_username = generate_username(first_name, last_name)
        
        # Obtener rol por defecto (Vendedor - nivel 4)
        try:
            default_position = PositionType.objects.get(
                hierarchy_level=4,  # Vendedor
                is_active=True
            )
        except PositionType.DoesNotExist:
            # Si no existe vendedor, usar el nivel más alto disponible
            default_position = PositionType.objects.filter(
                is_active=True
            ).order_by('-hierarchy_level').first()
            
            if not default_position:
                return JsonResponse({
                    'success': False,
                    'message': 'No hay tipos de posición disponibles. Contacta al administrador.'
                })
        
        # Validaciones
        errors = {}
        
        if not first_name:
            errors['first_name'] = 'El nombre es requerido'
        
        if not last_name:
            errors['last_name'] = 'El apellido es requerido'
        
        if not email:
            errors['email'] = 'El email es requerido'
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = 'Ingresa un email válido (ejemplo: usuario@correo.com)'
            
            # Verificar unicidad del email
            if User.objects.filter(email=email).exists():
                errors['email'] = 'Ya existe un usuario registrado con este email'
        
        # Validación de contraseña robusta
        if not password:
            errors['password'] = 'La contraseña es requerida'
        else:
            password_errors = []
            
            # Mínimo 8 caracteres
            if len(password) < 8:
                password_errors.append('al menos 8 caracteres')
            
            # Debe contener mayúscula
            if not any(c.isupper() for c in password):
                password_errors.append('al menos una letra mayúscula')
            
            # Debe contener minúscula
            if not any(c.islower() for c in password):
                password_errors.append('al menos una letra minúscula')
            
            # Debe contener símbolo
            import string
            if not any(c in string.punctuation for c in password):
                password_errors.append('al menos un símbolo (!@#$%^&*)')
            
            # No debe contener nombre o apellido
            password_lower = password.lower()
            if first_name.lower() in password_lower or last_name.split()[0].lower() in password_lower:
                password_errors.append('no puede contener tu nombre o apellido')
            
            if password_errors:
                errors['password'] = f'La contraseña debe tener: {", ".join(password_errors)}'
        
        # El rol se asigna automáticamente por defecto (Vendedor)
        
        # Validaciones para campos obligatorios adicionales
        if not cedula:
            errors['cedula'] = 'La cédula de identidad es requerida'
        elif User.objects.filter(cedula=cedula).exists():
            errors['cedula'] = 'Ya existe un usuario registrado con esta cédula'
        
        if not telefono:
            errors['telefono'] = 'El número de teléfono es requerido'
        else:
            # Validar formato de teléfono boliviano: debe comenzar con 6 o 7 y tener 8 dígitos
            import re
            if not re.match(r'^[67]\d{7}$', telefono):
                errors['telefono'] = 'El teléfono debe comenzar con 6 ó 7 y tener exactamente 8 dígitos (ejemplo: 71234567)'
        
        if not fecha_nacimiento:
            errors['fecha_nacimiento'] = 'La fecha de nacimiento es requerida'
        else:
            fecha_obj = None
            try:
                from datetime import datetime, date
                fecha_obj = datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date()
                today = date.today()
                
                # Verificar que no sea fecha futura
                if fecha_obj > today:
                    errors['fecha_nacimiento'] = 'La fecha de nacimiento no puede ser en el futuro'
                # Verificar que no sea muy antigua (más de 120 años)
                elif today.year - fecha_obj.year > 120:
                    errors['fecha_nacimiento'] = 'La fecha no puede ser mayor a 120 años'
                # Verificar que sea mayor de edad (18 años)
                else:
                    # Calcular edad exacta
                    age = today.year - fecha_obj.year - ((today.month, today.day) < (fecha_obj.month, fecha_obj.day))
                    if age < 18:
                        errors['fecha_nacimiento'] = f'Debes ser mayor de edad para registrarte. Tu edad actual es {age} años'
                        
            except ValueError:
                errors['fecha_nacimiento'] = 'Formato de fecha inválido. Usa el formato DD/MM/AAAA'
        
        if not domicilio:
            errors['domicilio'] = 'La dirección de domicilio es requerida'
        
        # Validar coordenadas
        lat_decimal = None
        lng_decimal = None
        if latitud and longitud:
            try:
                lat_decimal = float(latitud)
                lng_decimal = float(longitud)
                
                # Validar rangos de coordenadas
                if not (-90 <= lat_decimal <= 90):
                    errors['latitud'] = 'La latitud debe estar entre -90 y 90'
                if not (-180 <= lng_decimal <= 180):
                    errors['longitud'] = 'La longitud debe estar entre -180 y 180'
            except ValueError:
                errors['coordenadas'] = 'Las coordenadas deben ser números válidos'
        
        # Validar foto de perfil
        if foto_perfil:
            # Validar tamaño (máximo 5MB)
            if foto_perfil.size > 5 * 1024 * 1024:
                errors['foto_perfil'] = 'La imagen no puede ser mayor a 5MB'
            
            # Validar tipo de archivo
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if foto_perfil.content_type not in allowed_types:
                errors['foto_perfil'] = 'Solo se permiten archivos JPG, PNG o GIF'
        
        # Si hay errores, retornarlos
        if errors:
            return JsonResponse({
                'success': False,
                'errors': errors
            })
        
        # Crear usuario y membresía en una transacción
        with transaction.atomic():
            # Crear el usuario (INACTIVO por defecto)
            user = User.objects.create_user(
                username=generated_username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False  # IMPORTANTE: Usuario inactivo hasta que supervisor lo active
            )
            
            # Agregar los campos adicionales
            if cedula:
                user.cedula = cedula
            if telefono:
                user.telefono = telefono
            if fecha_obj:
                user.fecha_nacimiento = fecha_obj
            if domicilio:
                user.domicilio = domicilio
            if lat_decimal is not None and lng_decimal is not None:
                user.latitud = lat_decimal
                user.longitud = lng_decimal
            if foto_perfil:
                user.foto_perfil = foto_perfil
            
            user.save()
            
            # Crear la membresía de equipo (también inactiva)
            membership = TeamMembership.objects.create(
                user=user,
                organizational_unit=unit,
                position_type=default_position,
                assignment_type='PERMANENT',
                status='SUSPENDED',  # Status suspendido hasta aprobación
                is_active=False,     # Membresía inactiva hasta aprobación
                notes=f'Auto-registro público desde {request.META.get("REMOTE_ADDR", "IP desconocida")}. Rol asignado automáticamente: {default_position.name}'
            )
        
        # Generar URL de confirmación
        confirmation_url = f"https://tmkorban.duckdns.org{reverse('sales_team_management:public_register_success', kwargs={'username': user.username})}"
        
        return JsonResponse({
            'success': True,
            'message': 'Registro completado exitosamente',
            'confirmation_url': confirmation_url,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'team': unit.name
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al procesar el registro: {str(e)}'
        })


def public_register_success(request, username):
    """Página de confirmación de registro exitoso"""
    
    user = get_object_or_404(User, username=username, is_active=False)
    membership = TeamMembership.objects.filter(user=user, is_active=False).first()
    
    context = {
        'user': user,
        'membership': membership
    }
    
    return render(request, 'sales_team_management/public/success.html', context)