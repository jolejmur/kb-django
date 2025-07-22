#!/bin/bash

# Script para iniciar el CRM completo
# Ejecutar: ./start-crm.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Iniciando CRM Django con Nginx + SSL${NC}"

# Verificar si Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker no está ejecutándose. Inicia Docker primero.${NC}"
    exit 1
fi

# Verificar si existe certificado SSL
if [ ! -f "docker/certbot/conf/live/korban.duckdns.org/fullchain.pem" ]; then
    echo -e "${YELLOW}⚠️  No se encontró certificado SSL${NC}"
    echo -e "${YELLOW}💡 Ejecuta primero: ./init-ssl.sh${NC}"
    exit 1
fi

# Función para verificar si Django está corriendo
check_django() {
    if curl -s http://localhost:8000 > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Verificar si Django está corriendo
echo -e "${YELLOW}🔍 Verificando Django en localhost:8000...${NC}"
if check_django; then
    echo -e "${GREEN}✅ Django está corriendo${NC}"
else
    echo -e "${RED}❌ Django no está corriendo en localhost:8000${NC}"
    echo -e "${YELLOW}💡 Inicia Django con: python manage.py runserver${NC}"
    echo -e "${YELLOW}📝 O ejecuta en otra terminal:${NC}"
    echo "   cd /Users/jorgemucarcel/Desktop/kb-django-main"
    echo "   python manage.py runserver"
    echo ""
    read -p "¿Quieres continuar sin Django? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Iniciar servicios Docker
echo -e "${YELLOW}🐳 Iniciando servicios Docker...${NC}"
docker-compose up -d

# Verificar que Nginx esté corriendo
echo -e "${YELLOW}⏳ Verificando servicios...${NC}"
sleep 5

if docker-compose ps | grep -q "nginx.*Up"; then
    echo -e "${GREEN}✅ Nginx está corriendo${NC}"
else
    echo -e "${RED}❌ Error al iniciar Nginx${NC}"
    echo -e "${YELLOW}💡 Verifica los logs: docker-compose logs nginx${NC}"
    exit 1
fi

# Verificar acceso HTTPS
echo -e "${YELLOW}🔍 Verificando acceso HTTPS...${NC}"
if curl -s -I https://korban.duckdns.org > /dev/null; then
    echo -e "${GREEN}✅ HTTPS funcionando correctamente${NC}"
    echo -e "${GREEN}🎉 ¡CRM disponible en: https://korban.duckdns.org${NC}"
else
    echo -e "${YELLOW}⚠️  HTTPS no responde (puede tomar unos segundos)${NC}"
    echo -e "${YELLOW}💡 Verifica manualmente: https://korban.duckdns.org${NC}"
fi

echo -e "${BLUE}📋 Estado de servicios:${NC}"
docker-compose ps

echo -e "${YELLOW}📋 Comandos útiles:${NC}"
echo "  - Ver logs Nginx: docker-compose logs nginx"
echo "  - Ver logs en tiempo real: docker-compose logs -f nginx"
echo "  - Reiniciar Nginx: docker-compose restart nginx"
echo "  - Parar servicios: docker-compose down"
echo "  - Renovar certificado: docker-compose run --rm certbot-renew"