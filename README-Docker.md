y d# 🐳 Publicación del CRM con Docker + SSL

Este setup te permite publicar tu CRM Django con **Nginx + SSL válido de Let's Encrypt** mientras Django sigue corriendo localmente en desarrollo.

## 🚀 Configuración Inicial

### 1. Preparar el entorno

```bash
# Asegúrate de estar en el directorio del proyecto
cd /Users/jorgemucarcel/Desktop/kb-django-main

# Verificar que Docker esté corriendo
docker --version
```

### 2. Configurar el email para Let's Encrypt

Edita el archivo `docker-compose.yml` y cambia:
```yaml
--email tu-email@example.com
```
Por tu email real.

### 3. Verificar configuración de MikroTik

Asegúrate de que tu MikroTik tenga configurados estos redirects:
- Puerto **80** → IP de tu PC
- Puerto **443** → IP de tu PC
- Puerto **8095** → IP de tu PC (opcional)

### 4. Verificar Django local

```bash
# Inicia Django en otra terminal
python manage.py runserver
```

Verifica que responda en `http://localhost:8000`

## 🔐 Obtener Certificado SSL (Primera vez)

```bash
# Ejecutar SOLO la primera vez
./init-ssl.sh
```

Este script:
1. ✅ Verifica que Docker esté corriendo
2. ✅ Configura Nginx temporalmente (sin SSL)
3. ✅ Verifica que `korban.duckdns.org` sea accesible
4. ✅ Solicita certificado SSL a Let's Encrypt
5. ✅ Activa la configuración SSL completa

## 🚀 Iniciar el CRM

```bash
# Iniciar servicios (uso diario)
./start-crm.sh
```

Tu CRM estará disponible en: **https://korban.duckdns.org**

## 🔄 Renovar Certificado SSL

```bash
# Renovar certificado (cada 60-90 días)
./renew-ssl.sh
```

## 📋 Comandos Útiles

```bash
# Ver logs de Nginx
docker-compose logs nginx

# Ver logs en tiempo real
docker-compose logs -f nginx

# Verificar estado de servicios
docker-compose ps

# Reiniciar solo Nginx
docker-compose restart nginx

# Parar todos los servicios
docker-compose down

# Limpiar todo (cuidado: elimina certificados)
docker-compose down -v
```

## 🔧 Estructura de Archivos

```
kb-django-main/
├── docker-compose.yml          # Configuración Docker
├── docker/
│   ├── nginx/conf.d/
│   │   └── default.conf        # Configuración Nginx
│   └── certbot/
│       ├── conf/               # Certificados SSL
│       └── www/                # Validación Let's Encrypt
├── init-ssl.sh                 # Script inicial SSL
├── start-crm.sh               # Script para iniciar CRM
├── renew-ssl.sh               # Script renovar SSL
└── README-Docker.md           # Esta documentación
```

## 🛠️ Troubleshooting

### Error: "Docker no está ejecutándose"
```bash
# Iniciar Docker Desktop
open -a Docker
```

### Error: "No se puede acceder a korban.duckdns.org"
1. Verifica que `korban.duckdns.org` apunte a tu IP pública
2. Verifica redirects en MikroTik (puerto 80 → tu PC)
3. Verifica que Django esté corriendo: `curl http://localhost:8000`

### Error: "Certificado no válido"
```bash
# Verificar certificado
docker run --rm -v $(pwd)/docker/certbot/conf:/etc/letsencrypt certbot/certbot certificates

# Renovar manualmente
./renew-ssl.sh
```

### Error: "Nginx no inicia"
```bash
# Ver logs detallados
docker-compose logs nginx

# Verificar configuración
docker-compose config
```

## 📧 Configuración para Meta Business

Con el SSL válido, ahora puedes:
1. ✅ Configurar webhooks de WhatsApp Business
2. ✅ Usar la API de Facebook sin problemas
3. ✅ Configurar dominios verificados en Meta Business

## 🔒 Seguridad

- ✅ Certificado SSL válido (A+ en SSL Labs)
- ✅ Headers de seguridad configurados
- ✅ Redirección automática HTTP → HTTPS
- ✅ Protección contra XSS y clickjacking

## 📱 Próximos Pasos

1. Una vez que funcione todo, puedes configurar auto-renovación:
```bash
# Agregar a crontab para renovar automáticamente
0 12 * * * /Users/jorgemucarcel/Desktop/kb-django-main/renew-ssl.sh
```

2. Cuando estés listo para producción:
   - Migrar de SQLite a PostgreSQL
   - Usar Docker también para Django
   - Configurar backups automáticos