#!/bin/bash

# Script para renovar certificado SSL
# Ejecutar: ./renew-ssl.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Renovando certificado SSL...${NC}"

# Verificar si Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker no está ejecutándose. Inicia Docker primero.${NC}"
    exit 1
fi

# Renovar certificado
echo -e "${YELLOW}🔐 Intentando renovar certificado...${NC}"
docker-compose run --rm certbot-renew

# Verificar si hay nuevos certificados
if docker-compose run --rm certbot-renew 2>&1 | grep -q "Certificate not yet due for renewal"; then
    echo -e "${GREEN}✅ Certificado aún válido, no necesita renovación${NC}"
else
    echo -e "${GREEN}✅ Certificado renovado, reiniciando Nginx...${NC}"
    docker-compose restart nginx
    echo -e "${GREEN}🎉 ¡Certificado renovado exitosamente!${NC}"
fi

# Mostrar información del certificado
echo -e "${YELLOW}📋 Información del certificado:${NC}"
if [ -f "docker/certbot/conf/live/korban.duckdns.org/fullchain.pem" ]; then
    docker run --rm -v $(pwd)/docker/certbot/conf:/etc/letsencrypt certbot/certbot certificates
else
    echo -e "${RED}❌ No se encontró certificado${NC}"
fi