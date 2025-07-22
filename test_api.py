#!/usr/bin/env python
"""
Script para probar la API de conversaciones
"""

import os
import sys
import django
from django.test import RequestFactory
from django.contrib.auth import get_user_model

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.whatsapp_business.views import get_conversations
from apps.whatsapp_business.models import Conversacion

def test_api():
    print("🧪 Probando API de conversaciones...")
    
    # Crear request factory
    factory = RequestFactory()
    
    # Crear request para API
    request = factory.get('/marketing/api/conversations/?estado=todos&limit=20')
    
    # Obtener un usuario para la prueba
    User = get_user_model()
    user = User.objects.first()
    if not user:
        print("❌ No hay usuarios en la base de datos")
        return
    
    request.user = user
    print(f"👤 Usuario de prueba: {user}")
    
    # Simular que tiene permisos
    def mock_has_module_access(module_name):
        print(f"🔑 Verificando acceso a módulo: {module_name}")
        return True
    
    user.has_module_access = mock_has_module_access
    
    try:
        # Probar la vista directamente
        response = get_conversations(request)
        print(f"📡 Respuesta status: {response.status_code}")
        
        if hasattr(response, 'content'):
            import json
            content = json.loads(response.content.decode('utf-8'))
            print(f"📊 Contenido: {content}")
            
            if content.get('success'):
                print(f"✅ Conversaciones encontradas: {len(content['conversations'])}")
                for conv in content['conversations']:
                    print(f"  - {conv['cliente']['nombre']} ({conv['estado']})")
            else:
                print(f"❌ Error en respuesta: {content.get('error')}")
    
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_api()