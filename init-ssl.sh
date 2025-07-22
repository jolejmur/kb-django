#!/bin/bash

# Script para inicializar SSL con Let's Encrypt
# Ejecutar: ./init-ssl.sh

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando configuración SSL para korban.duckdns.org${NC}"

# Verificar si Docker está corriendo
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker no está ejecutándose. Inicia Docker primero.${NC}"
    exit 1
fi

# Crear directorios necesarios
echo -e "${YELLOW}📁 Creando directorios necesarios...${NC}"
mkdir -p docker/nginx/conf.d docker/certbot/www docker/certbot/conf

# Verificar que el archivo de configuración de Nginx existe
if [ ! -f "docker/nginx/conf.d/default.conf" ]; then
    echo -e "${RED}❌ Archivo de configuración de Nginx no encontrado${NC}"
    exit 1
fi

# Crear configuración temporal de Nginx sin SSL
echo -e "${YELLOW}📝 Creando configuración temporal de Nginx...${NC}"
cat > docker/nginx/conf.d/temp.conf << 'EOF'
server {
    listen 80;
    server_name korban.duckdns.org;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://host.docker.internal:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Renombrar configuración original
mv docker/nginx/conf.d/default.conf docker/nginx/conf.d/default.conf.ssl

# Usar configuración temporal
mv docker/nginx/conf.d/temp.conf docker/nginx/conf.d/default.conf

echo -e "${YELLOW}🌐 Iniciando Nginx temporalmente...${NC}"
docker-compose up -d nginx

echo -e "${YELLOW}⏳ Esperando que Nginx esté listo...${NC}"
sleep 10

# Verificar que korban.duckdns.org está accesible
echo -e "${YELLOW}🔍 Verificando acceso a korban.duckdns.org...${NC}"
if curl -s -I http://korban.duckdns.org > /dev/null; then
    echo -e "${GREEN}✅ Dominio accesible${NC}"
else
    echo -e "${RED}❌ No se puede acceder a korban.duckdns.org${NC}"
    echo -e "${YELLOW}💡 Verifica que:${NC}"
    echo "   - El puerto 80 esté redirigido a tu PC en el MikroTik"
    echo "   - korban.duckdns.org apunte a tu IP pública"
    echo "   - Tu Django esté corriendo en localhost:8000"
    exit 1
fi

echo -e "${YELLOW}🔐 Solicitando certificado SSL...${NC}"
docker-compose run --rm certbot

# Verificar que el certificado se obtuvo correctamente
if [ -f "docker/certbot/conf/live/korban.duckdns.org/fullchain.pem" ]; then
    echo -e "${GREEN}✅ Certificado SSL obtenido exitosamente${NC}"
    
    # Restaurar configuración con SSL
    echo -e "${YELLOW}🔄 Activando configuración SSL...${NC}"
    mv docker/nginx/conf.d/default.conf docker/nginx/conf.d/temp.conf
    mv docker/nginx/conf.d/default.conf.ssl docker/nginx/conf.d/default.conf
    
    # Reiniciar Nginx con SSL
    echo -e "${YELLOW}🔄 Reiniciando Nginx con SSL...${NC}"
    docker-compose restart nginx
    
    echo -e "${GREEN}🎉 ¡Configuración SSL completada!${NC}"
    echo -e "${GREEN}✅ Tu CRM está disponible en: https://korban.duckdns.org${NC}"
    
else
    echo -e "${RED}❌ Error al obtener certificado SSL${NC}"
    echo -e "${YELLOW}💡 Verifica los logs: docker-compose logs certbot${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Comandos útiles:${NC}"
echo "  - Ver logs: docker-compose logs nginx"
echo "  - Renovar certificado: docker-compose run --rm certbot-renew"
echo "  - Reiniciar Nginx: docker-compose restart nginx"
echo "  - Parar todo: docker-compose down"