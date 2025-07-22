#!/usr/bin/env python3

import os
import sys
import django

# Configurar Django
script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = script_dir
sys.path.insert(0, project_dir)
os.chdir(project_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.real_estate_projects.models import Proyecto, Fase, Inmueble
from django.db.models import Count, Q

print("=== DEBUG FASES Y INMUEBLES ===")

# Obtener todos los proyectos
proyectos = Proyecto.objects.filter(activo=True)

for proyecto in proyectos:
    print(f"\n🏢 PROYECTO: {proyecto.nombre}")
    print(f"   ID: {proyecto.id}")
    print(f"   Tipo: {proyecto.tipo}")
    
    # Fases reales en la BD
    fases_reales = proyecto.fases.all()
    print(f"   Fases en BD: {fases_reales.count()}")
    
    for fase in fases_reales:
        print(f"     📁 Fase {fase.numero_fase}: {fase.nombre} (ID: {fase.id}, activo: {fase.activo})")
        
        # Inmuebles de esta fase
        inmuebles = fase.inmuebles.all()
        print(f"        Inmuebles: {inmuebles.count()}")
        
        for inmueble in inmuebles[:5]:  # Solo mostrar primeros 5
            print(f"          🏠 {inmueble.codigo} (disponible: {inmueble.disponible})")
    
    # Verificar counts con la consulta de la vista
    stats_vista = Proyecto.objects.filter(id=proyecto.id).annotate(
        total_fases=Count('fases', filter=Q(fases__activo=True)),
        count_inmuebles=Count('fases__inmuebles', filter=Q(fases__activo=True, fases__inmuebles__disponible=True), distinct=True)
    ).first()
    
    print(f"   📊 STATS DE LA VISTA:")
    print(f"      total_fases: {stats_vista.total_fases}")
    print(f"      count_inmuebles: {stats_vista.count_inmuebles}")
    
    # Verificar counts directos
    fases_activas = proyecto.fases.filter(activo=True).count()
    inmuebles_disponibles = Inmueble.objects.filter(
        fase__proyecto=proyecto,
        fase__activo=True,
        disponible=True
    ).count()
    
    print(f"   📊 COUNTS DIRECTOS:")
    print(f"      fases_activas: {fases_activas}")
    print(f"      inmuebles_disponibles: {inmuebles_disponibles}")

print(f"\n🔍 TOTAL PROYECTOS: {proyectos.count()}")