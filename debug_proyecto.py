#!/usr/bin/env python3

# Script temporal para debuggear la creación de proyectos
# Simula exactamente lo que haría el formulario

def simulate_form_data():
    """Simula los datos que enviaría el formulario para 2 fases con 4 inmuebles cada una"""
    
    # Datos que el usuario ingresaría
    form_data = {
        'numero_fases': 2,          # 2 fases
        'numero_torres': 1,         # 1 torre por fase  
        'pisos_inicio': 1,          # piso 1
        'pisos_fin': 2,             # piso 2 (2 pisos total)
        'departamentos_por_piso': 2, # 2 departamentos por piso
        'tipo': 'departamentos'
    }
    
    print("=== DATOS DEL FORMULARIO ===")
    for key, value in form_data.items():
        print(f"{key}: {value}")
    
    # Simular el parse que hace la función _parse_dynamic_structure
    structure_data = {'fases': {}}
    
    numero_fases = form_data.get('numero_fases') or 1
    print(f"\nNúmero de fases a crear: {numero_fases}")
    
    for fase_num in range(1, numero_fases + 1):
        fase_data = {
            'nombre': f'Fase {fase_num}',
            'comercializable': False,
            'torres': {},
            'sectores': None
        }
        
        if form_data['tipo'] == 'departamentos':
            numero_torres = form_data.get('numero_torres') or 1
            print(f"  Fase {fase_num}: creando {numero_torres} torres")
            
            for torre_num in range(1, numero_torres + 1):
                pisos_inicio = form_data.get('pisos_inicio') or 1
                pisos_fin = form_data.get('pisos_fin') or 10
                deptos_piso = form_data.get('departamentos_por_piso') or 4
                
                print(f"    Torre {torre_num}: pisos {pisos_inicio}-{pisos_fin}, {deptos_piso} deptos/piso")
                
                fase_data['torres'][torre_num] = {
                    'nombre': f'Torre {torre_num}',
                    'pisos_inicio': pisos_inicio,
                    'pisos_fin': pisos_fin,
                    'deptos_piso': deptos_piso,
                    'comercializable': False
                }
        
        structure_data['fases'][fase_num] = fase_data
    
    print(f"\n=== ESTRUCTURA GENERADA ===")
    print(f"Total fases: {len(structure_data['fases'])}")
    
    total_inmuebles = 0
    for fase_num, fase_info in structure_data['fases'].items():
        print(f"\nFase {fase_num}:")
        if fase_info.get('torres'):
            for torre_num, torre_info in fase_info['torres'].items():
                pisos_inicio = torre_info.get('pisos_inicio')
                pisos_fin = torre_info.get('pisos_fin') 
                deptos_piso = torre_info.get('deptos_piso')
                
                # Calcular inmuebles de esta torre
                total_pisos = pisos_fin - pisos_inicio + 1
                inmuebles_torre = total_pisos * deptos_piso
                total_inmuebles += inmuebles_torre
                
                print(f"  Torre {torre_num}: {total_pisos} pisos × {deptos_piso} deptos = {inmuebles_torre} inmuebles")
    
    print(f"\nTOTAL INMUEBLES CALCULADOS: {total_inmuebles}")
    print("ESPERADO: 8 inmuebles (2 fases × 1 torre × 2 pisos × 2 deptos)")
    
    return structure_data

if __name__ == "__main__":
    simulate_form_data()