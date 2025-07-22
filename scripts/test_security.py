#!/usr/bin/env python
"""
Script para probar el sistema de seguridad contra fuerza bruta
"""
import requests
import time

def test_brute_force_protection():
    """Probar protección contra fuerza bruta"""
    
    login_url = "http://127.0.0.1:8000/accounts/login/"
    
    print("🔬 Probando protección contra fuerza bruta...")
    print(f"URL de prueba: {login_url}")
    
    # Datos de login incorrectos
    bad_credentials = {
        'username': 'fake_user',
        'password': 'wrong_password'
    }
    
    try:
        session = requests.Session()
        
        # Obtener token CSRF
        print("1. Obteniendo token CSRF...")
        response = session.get(login_url)
        
        if 'csrftoken' in session.cookies:
            csrf_token = session.cookies['csrftoken']
        else:
            print("❌ No se pudo obtener token CSRF")
            return
        
        bad_credentials['csrfmiddlewaretoken'] = csrf_token
        
        print("2. Enviando múltiples intentos fallidos...")
        
        for attempt in range(7):  # Intentar 7 veces (más del límite de 5)
            print(f"   Intento {attempt + 1}...")
            
            response = session.post(login_url, data=bad_credentials)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 429:
                print("✅ ¡BLOQUEADO! El sistema detectó el ataque")
                print("   La IP fue bloqueada correctamente")
                break
            elif "bloqueado" in response.text.lower():
                print("✅ ¡BLOQUEADO! Página de bloqueo mostrada")
                break
            
            time.sleep(1)  # Esperar 1 segundo entre intentos
        
        else:
            print("⚠️  No se detectó bloqueo. Verifica la configuración.")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        print("   Asegúrate de que el servidor esté corriendo en 127.0.0.1:8000")

if __name__ == "__main__":
    test_brute_force_protection()