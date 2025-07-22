# Django CRM - Configuración de Producción

Este documento describe cómo desplegar Django CRM en producción usando Docker y PostgreSQL.

## 🏗️ Arquitectura de Producción

- **Django**: Aplicación web con Gunicorn
- **PostgreSQL**: Base de datos principal
- **Redis**: Cache y sesiones
- **Nginx**: Proxy reverso y archivos estáticos
- **Certbot**: Certificados SSL automáticos

## 📋 Requisitos Previos

- Docker >= 20.10
- Docker Compose >= 2.0
- Servidor con al menos 2GB RAM
- Dominio configurado (para SSL)

## 🚀 Despliegue Rápido

### 1. Preparar el entorno

```bash
# Clonar el repositorio
git clone <your-repo-url>
cd django-crm

# Copiar y configurar variables de entorno
cp .env.production.example .env.production
nano .env.production
```

### 2. Configurar variables de entorno

Edita `.env.production` con tus configuraciones:

```bash
# Configuración básica
PRODUCTION=true
SECRET_KEY=your-super-secret-key-change-this
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Base de datos
POSTGRES_DB=django_crm_production
POSTGRES_USER=django_user
POSTGRES_PASSWORD=your-secure-password

# Administrador
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=your-secure-admin-password

# Email (opcional)
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### 3. Ejecutar script de configuración

```bash
./start-production.sh
```

Este script:
- ✅ Verifica dependencias
- 🔨 Construye las imágenes Docker
- 🗄️ Configura PostgreSQL y Redis
- 🌐 Inicia la aplicación Django
- 🔄 Configura Nginx como proxy reverso
- 📦 Ejecuta el script de configuración inicial

## 📊 Verificación del Despliegue

### Verificar servicios
```bash
docker-compose -f docker-compose.production.yml ps
```

### Ver logs
```bash
# Todos los servicios
docker-compose -f docker-compose.production.yml logs -f

# Solo Django
docker-compose -f docker-compose.production.yml logs -f web

# Solo base de datos
docker-compose -f docker-compose.production.yml logs -f postgres
```

### Acceder a la aplicación
- **URL**: `http://your-server-ip:8000` o `https://yourdomain.com`
- **Usuario**: El configurado en `ADMIN_USERNAME`
- **Contraseña**: La configurada en `ADMIN_PASSWORD`

## 🔧 Configuración Inicial

### Roles y Permisos Creados

El script `production_setup.py` crea automáticamente:

1. **Super Admin**: Acceso completo a todos los módulos
2. **Registro**: Acceso a gestión de equipos y jerarquía
3. **Ventas**: Solo acceso al perfil de usuario
4. **Team Leader**: Solo acceso al perfil de usuario  
5. **Jefe de Equipo**: Solo acceso al perfil de usuario
6. **Gerente de Proyecto**: Solo acceso al perfil de usuario

### Módulos del Sistema

El sistema incluye 27 módulos organizados en 6 categorías:

- **Administración del Sistema** (2 módulos)
- **Gestión de Usuarios** (3 módulos)
- **Proyectos Inmobiliarios** (4 módulos)
- **Equipos de Venta** (6 módulos)
- **CRM y Comunicaciones** (6 módulos)
- **Reportes y Analytics** (6 módulos)

## 🔒 Configuración SSL (HTTPS)

### Para dominios con Let's Encrypt

```bash
# Configurar SSL automático
./setup-ssl.sh yourdomain.com
```

### SSL manual
1. Coloca tus certificados en `docker/certbot/conf/live/yourdomain.com/`
2. Actualiza `nginx.production.conf` con tu dominio
3. Reinicia Nginx: `docker-compose -f docker-compose.production.yml restart nginx`

## 💾 Backup y Mantenimiento

### Backup de base de datos
```bash
# Crear backup
docker-compose -f docker-compose.production.yml exec postgres pg_dump -U django_user django_crm > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
docker-compose -f docker-compose.production.yml exec -T postgres psql -U django_user -d django_crm < backup_file.sql
```

### Actualizar aplicación
```bash
# Parar servicios
docker-compose -f docker-compose.production.yml down

# Actualizar código
git pull origin main

# Reconstruir y reiniciar
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d
```

### Logs y monitoreo
```bash
# Rotar logs
docker-compose -f docker-compose.production.yml exec nginx logrotate /etc/logrotate.conf

# Espacio en disco
docker system df
docker system prune -a  # Limpiar imágenes no utilizadas
```

## 🔍 Solución de Problemas

### Django no inicia
```bash
# Ver logs detallados
docker-compose -f docker-compose.production.yml logs web

# Conectar a contenedor
docker-compose -f docker-compose.production.yml exec web bash
```

### Error de base de datos
```bash
# Verificar conexión
docker-compose -f docker-compose.production.yml exec postgres psql -U django_user -d django_crm -c "SELECT version();"

# Recrear base de datos
docker-compose -f docker-compose.production.yml down
docker volume rm django-crm_postgres_data
docker-compose -f docker-compose.production.yml up -d
```

### Problemas de permisos
```bash
# Ejecutar script de sincronización
docker-compose -f docker-compose.production.yml exec web python scripts/sync_role_groups_to_users.py
```

## 📈 Optimización de Rendimiento

### Variables de entorno recomendadas
```bash
# Workers de Gunicorn (2 * CPU cores + 1)
GUNICORN_WORKERS=5

# Conexiones de base de datos
DB_CONN_MAX_CONNECTIONS=20

# Cache Redis
REDIS_MAX_CONNECTIONS=50
```

### Configuración de Nginx
- Rate limiting configurado por defecto
- Archivos estáticos con cache de 30 días
- Compresión Gzip habilitada
- Headers de seguridad configurados

## 🛡️ Seguridad

### Configuraciones aplicadas
- ✅ HTTPS redirect automático
- ✅ Headers de seguridad
- ✅ Rate limiting en login y API
- ✅ Cookies seguras
- ✅ Protección CSRF
- ✅ Usuario no-root en containers

### Recomendaciones adicionales
1. Cambiar contraseñas por defecto
2. Configurar firewall (ufw)
3. Actualizar sistema operativo regularmente
4. Monitorear logs de seguridad
5. Configurar backups automáticos

## 📞 Soporte

Para problemas o consultas:
1. Revisar logs: `docker-compose logs`
2. Verificar configuración de variables de entorno
3. Consultar documentación de Django
4. Revisar issues en GitHub

## 🔄 Comandos Útiles

```bash
# Iniciar todos los servicios
docker-compose -f docker-compose.production.yml up -d

# Parar todos los servicios
docker-compose -f docker-compose.production.yml down

# Reiniciar un servicio específico
docker-compose -f docker-compose.production.yml restart web

# Ver estado de servicios
docker-compose -f docker-compose.production.yml ps

# Ejecutar comandos Django
docker-compose -f docker-compose.production.yml exec web python manage.py <command>

# Acceder a shell Django
docker-compose -f docker-compose.production.yml exec web python manage.py shell

# Ver recursos utilizados
docker stats
```

---

**¡Tu Django CRM está listo para producción! 🎉**