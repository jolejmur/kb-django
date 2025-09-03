"""
Management command to add security decorators to ALL view functions
"""
import os
import re
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Add security decorators to all view functions'

    def handle(self, *args, **options):
        self.stdout.write('🔒 SECURING ALL VIEW FUNCTIONS...')
        
        # Definir archivos y sus decoradores correspondientes
        view_files = {
            'jerarquia.py': {
                'decorator': '@hierarchy_module_required',
                'import': 'from ..decorators_modules import hierarchy_module_required'
            },
            'equipos.py': {
                'decorator': '@team_management_module_required', 
                'import': 'from ..decorators_modules import team_management_module_required'
            },
            'comisiones.py': {
                'decorator': '@commissions_module_required',
                'import': 'from ..decorators_modules import commissions_module_required'
            },
            'dashboard.py': {
                'decorator': '@dashboard_module_required',
                'import': 'from ..decorators_modules import dashboard_module_required'
            }
        }
        
        views_dir = 'apps/sales_team_management/views/'
        
        for filename, config in view_files.items():
            filepath = os.path.join(views_dir, filename)
            if os.path.exists(filepath):
                self.process_file(filepath, config, filename)
            else:
                self.stdout.write(f'⚠️  File not found: {filepath}')
    
    def process_file(self, filepath, config, filename):
        self.stdout.write(f'\\n📝 Processing {filename}...')
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar si ya tiene el import
        if config['import'] not in content:
            # Agregar import después de los otros imports
            import_pattern = r'(from django\\.http import [^\\n]+\\n)'
            if re.search(import_pattern, content):
                content = re.sub(
                    import_pattern, 
                    f'\\1{config["import"]}\\n',
                    content
                )
            else:
                # Si no encuentra el patrón, agregar después del último import
                lines = content.split('\\n')
                import_added = False
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        continue
                    else:
                        lines.insert(i, config['import'])
                        import_added = True
                        break
                
                if import_added:
                    content = '\\n'.join(lines)
                    self.stdout.write(f'  ✓ Added import')
        
        # Encontrar todas las funciones def que reciben request
        function_pattern = r'(@[^\\n]*\\n)*def\\s+(\\w+)\\s*\\([^)]*request[^)]*\\):'
        functions = re.findall(function_pattern, content)
        
        secured_functions = 0
        
        # Para cada función, verificar si ya tiene el decorador
        for match in re.finditer(function_pattern, content):
            decorators = match.group(1) or ''
            func_name = match.group(2)
            
            # Saltar funciones que no necesitan decorador
            if func_name.startswith('ajax_') or func_name in ['permission_denied_view']:
                continue
            
            if config['decorator'].replace('@', '') not in decorators:
                # Agregar el decorador
                full_match = match.group(0)
                if decorators:
                    new_decorators = decorators + config['decorator'] + '\\n'
                else:
                    new_decorators = config['decorator'] + '\\n'
                
                new_function = new_decorators + f'def {func_name}' + full_match[full_match.find('('):]
                content = content.replace(full_match, new_function)
                secured_functions += 1
                self.stdout.write(f'  ✓ Secured function: {func_name}')
        
        # Escribir el archivo actualizado
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.stdout.write(f'  📊 Secured {secured_functions} functions in {filename}')
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ All view functions secured!')
        )