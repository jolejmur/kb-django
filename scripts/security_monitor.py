#!/usr/bin/env python
"""
Monitor y gestión del sistema de seguridad contra fuerza bruta
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.core.cache import cache
import time

def show_security_status():
    """Mostrar estado del sistema de seguridad"""
    print("🔐 ESTADO DEL SISTEMA DE SEGURIDAD")
    print("=" * 50)
    
    # Buscar IPs bloqueadas
    blocked_ips = []
    attempt_counts = []
    
    # Django cache no tiene scan, así que usaremos claves conocidas
    # En producción con Redis se podría usar SCAN
    test_ips = [
        '127.0.0.1', '192.168.1.1', '10.0.0.1', 
        '172.16.0.1', '203.0.113.1', '198.51.100.1'
    ]
    
    for ip in test_ips:
        blocked_until = cache.get(f'blocked_ip:{ip}')
        attempts = cache.get(f'login_attempts:{ip}', 0)
        
        if blocked_until:
            remaining = max(0, int(blocked_until - time.time()))
            blocked_ips.append((ip, remaining))
        elif attempts > 0:
            attempt_counts.append((ip, attempts))
    
    if blocked_ips:
        print("\n🚫 IPs BLOQUEADAS:")
        for ip, remaining in blocked_ips:
            mins = remaining // 60
            secs = remaining % 60
            print(f"   {ip} - Tiempo restante: {mins}m {secs}s")
    else:
        print("\n✅ No hay IPs bloqueadas actualmente")
    
    if attempt_counts:
        print("\n⚠️  IPs CON INTENTOS FALLIDOS:")
        for ip, attempts in attempt_counts:
            print(f"   {ip} - {attempts} intentos")
    else:
        print("\n✅ No hay intentos fallidos registrados")
    
    print(f"\n📊 CONFIGURACIÓN ACTUAL:")
    print(f"   Máximo intentos permitidos: 5")
    print(f"   Tiempo de bloqueo: 15 minutos")

def clear_blocked_ip(ip):
    """Desbloquear una IP específica"""
    blocked_until = cache.get(f'blocked_ip:{ip}')
    attempts = cache.get(f'login_attempts:{ip}', 0)
    
    if blocked_until or attempts > 0:
        cache.delete(f'blocked_ip:{ip}')
        cache.delete(f'login_attempts:{ip}')
        print(f"✅ IP {ip} desbloqueada y intentos eliminados")
    else:
        print(f"ℹ️  IP {ip} no estaba bloqueada")

def clear_all_blocks():
    """Limpiar todos los bloqueos (solo para testing)"""
    # En producción sería mejor con Redis SCAN
    test_ips = [
        '127.0.0.1', '192.168.1.1', '10.0.0.1', 
        '172.16.0.1', '203.0.113.1', '198.51.100.1',
        '::1'  # IPv6 localhost
    ]
    
    cleared = 0
    for ip in test_ips:
        blocked_until = cache.get(f'blocked_ip:{ip}')
        attempts = cache.get(f'login_attempts:{ip}', 0)
        
        if blocked_until or attempts > 0:
            cache.delete(f'blocked_ip:{ip}')
            cache.delete(f'login_attempts:{ip}')
            cleared += 1
    
    print(f"✅ {cleared} IPs desbloqueadas")

def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor de seguridad contra fuerza bruta')
    parser.add_argument('--status', action='store_true', help='Mostrar estado del sistema')
    parser.add_argument('--clear-ip', type=str, help='Desbloquear IP específica')
    parser.add_argument('--clear-all', action='store_true', help='Limpiar todos los bloqueos')
    
    args = parser.parse_args()
    
    if args.status:
        show_security_status()
    elif args.clear_ip:
        clear_blocked_ip(args.clear_ip)
    elif args.clear_all:
        clear_all_blocks()
    else:
        print("Uso:")
        print("  python scripts/security_monitor.py --status")
        print("  python scripts/security_monitor.py --clear-ip 192.168.1.100")
        print("  python scripts/security_monitor.py --clear-all")

if __name__ == "__main__":
    main()