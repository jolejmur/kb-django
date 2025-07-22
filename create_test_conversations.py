#!/usr/bin/env python
"""
Script para crear conversaciones de prueba para el módulo de supervisión de chat
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.whatsapp_business.models import Cliente, Conversacion, Mensaje
from django.contrib.auth import get_user_model

User = get_user_model()

def create_test_conversations():
    print("🚀 Creando conversaciones de prueba...")
    
    # Crear algunos clientes si no existen
    clientes_data = [
        {
            'nombre': 'Juan Pérez',
            'numero_whatsapp': '59165020724',
            'email': 'juan.perez@example.com',
            'ciudad': 'La Paz'
        },
        {
            'nombre': 'María García',
            'numero_whatsapp': '59172345678',
            'email': 'maria.garcia@example.com',
            'ciudad': 'Santa Cruz'
        },
        {
            'nombre': 'Carlos Mendoza',
            'numero_whatsapp': '59178901234',
            'email': 'carlos.mendoza@example.com',
            'ciudad': 'Cochabamba'
        },
        {
            'nombre': 'Ana Rodríguez',
            'numero_whatsapp': '59164567890',
            'email': 'ana.rodriguez@example.com',
            'ciudad': 'Oruro'
        }
    ]
    
    # Crear clientes
    for cliente_data in clientes_data:
        cliente, created = Cliente.objects.get_or_create(
            numero_whatsapp=cliente_data['numero_whatsapp'],
            defaults=cliente_data
        )
        if created:
            print(f"✅ Cliente creado: {cliente.nombre}")
        else:
            print(f"📋 Cliente existente: {cliente.nombre}")
    
    # Crear conversaciones
    clientes = Cliente.objects.all()
    for i, cliente in enumerate(clientes):
        # Crear conversación si no existe
        conversacion, created = Conversacion.objects.get_or_create(
            cliente=cliente,
            defaults={
                'numero_whatsapp': cliente.numero_whatsapp,
                'estado': 'abierta' if i < 3 else 'cerrada',
                'mensajes_no_leidos': 2 if i < 2 else 0,
                'ultimo_mensaje_at': timezone.now() - timedelta(minutes=i*10)
            }
        )
        
        if created:
            print(f"✅ Conversación creada: {cliente.nombre}")
            
            # Crear algunos mensajes de prueba
            mensajes_prueba = [
                {
                    'contenido': 'Hola, me interesa información sobre sus servicios',
                    'direccion': 'incoming',
                    'tipo': 'text',
                    'estado': 'leido',
                    'created_at': timezone.now() - timedelta(minutes=i*10 + 5)
                },
                {
                    'contenido': 'Hola! Gracias por contactarnos. ¿En qué podemos ayudarte?',
                    'direccion': 'outgoing',
                    'tipo': 'text',
                    'estado': 'leido',
                    'created_at': timezone.now() - timedelta(minutes=i*10 + 3)
                },
                {
                    'contenido': 'Quisiera saber más sobre precios y disponibilidad',
                    'direccion': 'incoming',
                    'tipo': 'text',
                    'estado': 'leido',
                    'created_at': timezone.now() - timedelta(minutes=i*10 + 1)
                }
            ]
            
            for msg_data in mensajes_prueba:
                Mensaje.objects.create(
                    conversacion=conversacion,
                    **msg_data
                )
            
            print(f"✅ Mensajes creados para {cliente.nombre}")
        else:
            print(f"📋 Conversación existente: {cliente.nombre}")
    
    print("\n🎉 ¡Conversaciones de prueba creadas exitosamente!")
    print(f"📊 Total de conversaciones: {Conversacion.objects.count()}")
    print(f"📊 Conversaciones abiertas: {Conversacion.objects.filter(estado='abierta').count()}")
    print(f"📊 Total de mensajes: {Mensaje.objects.count()}")
    print("\n🔗 Ahora puedes visitar: http://localhost:8000/marketing/supervision-chat/")

if __name__ == '__main__':
    create_test_conversations()