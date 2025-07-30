# Configuración de Subdominio QR Seguro

## 1. Configuración DNS
```
Agregar registro DNS:
qr.korban.duckdns.org -> IP del servidor
```

## 2. Configuración Nginx (/etc/nginx/sites-available/qr.korban.duckdns.org)
```nginx
server {
    listen 80;
    listen 443 ssl http2;
    server_name qr.korban.duckdns.org;
    
    # SSL (usar Let's Encrypt)
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;
    
    # Solo permitir acceso a endpoint específico de QR
    location ~ ^/([a-f0-9-]{36})/?$ {
        proxy_pass http://127.0.0.1:8000/qr-public/$1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Headers de seguridad
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
    }
    
    # Bloquear todo lo demás
    location / {
        return 404;
    }
}
```

## 3. Django URL específica para subdominio
```python
# En config/urls.py
path('qr-public/<uuid:codigo_qr>/', qr_public_secure_view, name='qr_public_secure'),
```

## 4. Vista segura optimizada
- Sin middleware de autenticación
- Solo acceso a datos específicos del QR
- Validación de UUID
- Rate limiting
- Logs de seguridad
```

## Ventajas de Seguridad:
✅ Separación completa del sistema principal
✅ Solo expone datos específicos del QR
✅ No acceso a base de datos completa
✅ Rate limiting por IP
✅ SSL/TLS obligatorio
✅ Headers de seguridad
✅ Logs de acceso independientes

## URL Final:
https://qr.korban.duckdns.org/{codigo_qr}/