#!/bin/bash
# Script de inicio rápido para producción - Django CRM

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 DJANGO CRM - CONFIGURACIÓN DE PRODUCCIÓN${NC}"
echo "=================================================="

# Verificar si Docker está instalado
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker no está instalado${NC}"
    echo "Por favor instala Docker desde https://docs.docker.com/get-docker/"
    exit 1
fi

# Verificar si Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Error: Docker Compose no está instalado${NC}"
    echo "Por favor instala Docker Compose desde https://docs.docker.com/compose/install/"
    exit 1
fi

# Verificar si el archivo .env.production existe
if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}⚠️  Archivo .env.production no encontrado${NC}"
    echo "Copiando archivo de ejemplo..."
    cp .env.production.example .env.production
    
    echo -e "${YELLOW}📝 IMPORTANTE:${NC}"
    echo "   1. Edita el archivo .env.production con tus configuraciones"
    echo "   2. Cambia las passwords por defecto"
    echo "   3. Configura tu dominio y certificados SSL"
    echo ""
    echo -e "${RED}¿Deseas continuar con la configuración de ejemplo? (y/N)${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Configuración cancelada. Edita .env.production y vuelve a ejecutar."
        exit 0
    fi
fi

# Cargar variables de entorno
source .env.production

echo -e "${GREEN}✅ Configuración cargada${NC}"

# Crear directorios necesarios
echo -e "${BLUE}📁 Creando directorios necesarios...${NC}"
mkdir -p logs
mkdir -p docker/postgres
mkdir -p docker/certbot/conf
mkdir -p docker/certbot/www
mkdir -p staticfiles
mkdir -p media

# Crear archivo de inicialización de PostgreSQL
cat > docker/postgres/init.sql << EOF
-- Inicialización de PostgreSQL para Django CRM
CREATE DATABASE ${POSTGRES_DB:-django_crm};
CREATE USER ${POSTGRES_USER:-django_user} WITH ENCRYPTED PASSWORD '${POSTGRES_PASSWORD:-django_password}';
GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB:-django_crm} TO ${POSTGRES_USER:-django_user};
ALTER USER ${POSTGRES_USER:-django_user} CREATEDB;
EOF

echo -e "${GREEN}✅ Directorios y archivos creados${NC}"

# Construir las imágenes
echo -e "${BLUE}🔨 Construyendo imágenes Docker...${NC}"
docker-compose -f docker-compose.production.yml build --no-cache

# Iniciar servicios de base de datos primero
echo -e "${BLUE}🗄️  Iniciando base de datos...${NC}"
docker-compose -f docker-compose.production.yml up -d postgres redis

# Esperar a que la base de datos esté lista
echo -e "${YELLOW}⏳ Esperando a que PostgreSQL esté listo...${NC}"
timeout=60
counter=0
until docker-compose -f docker-compose.production.yml exec -T postgres pg_isready -U ${POSTGRES_USER:-django_user} -d ${POSTGRES_DB:-django_crm}; do
    sleep 2
    counter=$((counter + 2))
    if [ $counter -ge $timeout ]; then
        echo -e "${RED}❌ Timeout esperando PostgreSQL${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ PostgreSQL está listo${NC}"

# Iniciar la aplicación web
echo -e "${BLUE}🌐 Iniciando aplicación Django...${NC}"
docker-compose -f docker-compose.production.yml up -d web

# Esperar a que la aplicación esté lista
echo -e "${YELLOW}⏳ Esperando a que Django esté listo...${NC}"
timeout=120
counter=0
until curl -f http://localhost:${WEB_PORT:-8000}/accounts/login/ > /dev/null 2>&1; do
    sleep 5
    counter=$((counter + 5))
    if [ $counter -ge $timeout ]; then
        echo -e "${RED}❌ Timeout esperando Django${NC}"
        docker-compose -f docker-compose.production.yml logs web
        exit 1
    fi
done

echo -e "${GREEN}✅ Django está listo${NC}"

# Iniciar Nginx
echo -e "${BLUE}🔄 Iniciando Nginx...${NC}"
docker-compose -f docker-compose.production.yml up -d nginx

# Mostrar estado de los servicios
echo -e "${BLUE}📊 Estado de los servicios:${NC}"
docker-compose -f docker-compose.production.yml ps

# Mostrar información de conexión
echo ""
echo "=================================================="
echo -e "${GREEN}🎉 ¡DESPLIEGUE COMPLETADO EXITOSAMENTE!${NC}"
echo "=================================================="
echo ""
echo -e "${BLUE}📋 INFORMACIÓN DE ACCESO:${NC}"
echo -e "   • Aplicación web: ${GREEN}http://localhost:${WEB_PORT:-8000}${NC}"
echo -e "   • Usuario admin: ${GREEN}${ADMIN_USERNAME:-admin}${NC}"

if [[ "${PRODUCTION:-}" != "true" ]]; then
    echo -e "   • Contraseña: ${GREEN}${ADMIN_PASSWORD:-admin123}${NC}"
fi

echo ""
echo -e "${BLUE}🐳 COMANDOS ÚTILES:${NC}"
echo "   • Ver logs: docker-compose -f docker-compose.production.yml logs -f"
echo "   • Parar servicios: docker-compose -f docker-compose.production.yml down"
echo "   • Reiniciar: docker-compose -f docker-compose.production.yml restart"
echo "   • Estado: docker-compose -f docker-compose.production.yml ps"
echo ""

# Configuración SSL (opcional)
if [[ "${DOMAIN_NAME:-}" != "yourdomain.com" && "${DOMAIN_NAME:-}" != "" ]]; then
    echo -e "${YELLOW}🔒 CONFIGURACIÓN SSL:${NC}"
    echo "   Para habilitar HTTPS, ejecuta:"
    echo "   ./setup-ssl.sh ${DOMAIN_NAME}"
    echo ""
fi

echo -e "${GREEN}✨ ¡Sistema listo para usar!${NC}"
echo -e "${BLUE}📊 Accede al dashboard desde tu navegador${NC}"