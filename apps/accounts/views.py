from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required
from django.contrib import messages
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.forms import ModelForm
from django import forms
from django.core.exceptions import ValidationError
from .forms import ModuleForm, RoleForm, UserForm, UserCreateForm
from .models import Role, MenuCategory, Navigation

User = get_user_model()


def custom_logout(request):
    """Custom logout view"""
    logout(request)
    request.session.flush()
    return redirect('accounts:login')


def is_admin(user):
    """Verifica si el usuario es administrador"""
    return user.is_superuser or user.is_staff


def can_edit_user(target_user, current_user):
    """Verifica si un usuario puede ser editado"""
    # El superadmin NO puede ser editado por nadie (ni siquiera por él mismo)
    if target_user.is_superuser:
        return False

    # Solo superadmins pueden editar otros usuarios
    return current_user.is_superuser


def can_delete_user(target_user, current_user):
    """Verifica si un usuario puede ser eliminado"""
    # El superadmin NUNCA puede ser eliminado
    if target_user.is_superuser:
        return False

    # No puedes eliminarte a ti mismo
    if target_user == current_user:
        return False

    # Solo superadmins pueden eliminar usuarios
    return current_user.is_superuser


# ============================================================
# VISTAS PARA MÓDULOS
# ============================================================

@login_required
@user_passes_test(is_admin)
def modules_list(request):
    """Lista todos los módulos disponibles"""
    modules = Group.objects.all().order_by('name')

    paginator = Paginator(modules, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'title': 'Módulos',
    }

    return render(request, 'accounts/modules/list.html', context)


@login_required
@user_passes_test(is_admin)
def module_create(request):
    """Crear un nuevo módulo"""
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Módulo creado exitosamente.')
            return redirect('accounts:modules_list')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ModuleForm()

    context = {
        'form': form,
        'title': 'Crear Módulo',
        'action': 'Crear',
        'help_text': 'Un módulo agrupa permisos relacionados con una área específica del sistema.'
    }

    return render(request, 'accounts/modules/form.html', context)


@login_required
@user_passes_test(is_admin)
def module_edit(request, pk):
    """Editar un módulo existente"""
    module = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            messages.success(request, 'Módulo actualizado exitosamente.')
            return redirect('accounts:modules_list')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = ModuleForm(instance=module)

    context = {
        'form': form,
        'module': module,
        'title': 'Editar Módulo',
        'action': 'Actualizar'
    }

    return render(request, 'accounts/modules/form.html', context)


@login_required
@user_passes_test(is_admin)
def module_delete(request, pk):
    """Eliminar un módulo"""
    module = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        try:
            # Verificar si se puede eliminar usando el método del modelo
            if not module.can_be_deleted():
                roles_using_module = module.roles.all()
                messages.error(
                    request,
                    f'No se puede eliminar el módulo "{module.name}" porque está siendo usado por los siguientes roles: '
                    f'{", ".join([role.name for role in roles_using_module])}'
                )
                return redirect('accounts:modules_list')

            module.delete()
            messages.success(request, 'Módulo eliminado exitosamente.')
            return redirect('accounts:modules_list')

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('accounts:modules_list')

    context = {
        'module': module,
        'title': 'Eliminar Módulo',
    }

    return render(request, 'accounts/modules/delete.html', context)


@login_required
@user_passes_test(is_admin)
def module_detail(request, pk):
    """Ver detalles de un módulo"""
    module = get_object_or_404(Group, pk=pk)
    permissions = module.permissions.all().order_by('content_type__app_label', 'name')
    roles = module.roles.all()

    try:
        navigation = module.navigation
    except:
        navigation = None

    context = {
        'module': module,
        'permissions': permissions,
        'roles': roles,
        'navigation': navigation,
        'title': f'Módulo: {module.name}',
    }

    return render(request, 'accounts/modules/detail.html', context)


# ============================================================
# VISTAS PARA ROLES
# ============================================================

@login_required
@user_passes_test(is_admin)
def roles_list(request):
    """Lista todos los roles disponibles"""
    roles = Role.objects.all().order_by('name')

    paginator = Paginator(roles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'title': 'Roles',
    }

    return render(request, 'accounts/roles/list.html', context)


@login_required
@user_passes_test(is_admin)
def role_create(request):
    """Crear un nuevo rol"""
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Rol creado exitosamente.')
            return redirect('accounts:roles_list')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = RoleForm()

    context = {
        'form': form,
        'title': 'Crear Rol',
        'action': 'Crear',
        'help_text': 'Un rol combina varios módulos para definir un puesto específico.'
    }

    return render(request, 'accounts/roles/form.html', context)


@login_required
@user_passes_test(is_admin)
def role_edit(request, pk):
    """Editar un rol existente"""
    role = get_object_or_404(Role, pk=pk)

    # ✅ VALIDACIÓN: Verificar si el rol se puede editar
    if not role.can_be_edited():
        messages.error(
            request,
            f'No se puede editar el rol "{role.name}" porque es un rol del sistema.'
        )
        return redirect('accounts:roles_list')

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, 'Rol actualizado exitosamente.')
            return redirect('accounts:roles_list')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = RoleForm(instance=role)

    context = {
        'form': form,
        'role': role,
        'title': 'Editar Rol',
        'action': 'Actualizar'
    }

    return render(request, 'accounts/roles/form.html', context)


@login_required
@user_passes_test(is_admin)
def role_delete(request, pk):
    """Eliminar un rol"""
    role = get_object_or_404(Role, pk=pk)

    if request.method == 'POST':
        try:
            # Usar el método del modelo que ya tiene las validaciones
            if not role.can_be_deleted():
                if role.is_system:
                    messages.error(
                        request,
                        f'No se puede eliminar el rol "{role.name}" porque es un rol del sistema.'
                    )
                else:
                    users_with_role = role.users.all()
                    messages.error(
                        request,
                        f'No se puede eliminar el rol "{role.name}" porque está siendo usado por {users_with_role.count()} usuarios. '
                        f'Primero cambia el rol de estos usuarios.'
                    )
                return redirect('accounts:roles_list')

            role.delete()
            messages.success(request, 'Rol eliminado exitosamente.')
            return redirect('accounts:roles_list')

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('accounts:roles_list')

    context = {
        'role': role,
        'title': 'Eliminar Rol',
    }

    return render(request, 'accounts/roles/delete.html', context)


@login_required
@user_passes_test(is_admin)
def role_detail(request, pk):
    """Ver detalles de un rol"""
    role = get_object_or_404(Role, pk=pk)
    modules = role.groups.all()
    users = role.users.all()

    all_permissions = set()
    for module in modules:
        all_permissions.update(module.permissions.all())

    context = {
        'role': role,
        'modules': modules,
        'users': users,
        'all_permissions': sorted(all_permissions, key=lambda p: (p.content_type.app_label, p.name)),
        'title': f'Rol: {role.name}',
    }

    return render(request, 'accounts/roles/detail.html', context)


# ============================================================
# VISTAS PARA USUARIOS - CON PROTECCIÓN DE SUPERADMIN
# ============================================================

@login_required
@user_passes_test(is_admin)
def users_list(request):
    """Lista todos los usuarios"""
    users = User.objects.all().order_by('username')

    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'title': 'Usuarios',
    }

    return render(request, 'accounts/users/list.html', context)


@login_required
@user_passes_test(is_admin)
def user_create(request):
    """Crear un nuevo usuario"""
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario creado exitosamente.')
            return redirect('accounts:users_list')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = UserCreateForm()

    context = {
        'form': form,
        'title': 'Crear Usuario',
        'action': 'Crear'
    }

    return render(request, 'accounts/users/form.html', context)


@login_required
@user_passes_test(is_admin)
def user_edit(request, pk):
    """Editar un usuario existente - CON PROTECCIÓN DE SUPERADMIN"""
    user_obj = get_object_or_404(User, pk=pk)

    # ✅ PROTECCIÓN: Verificar si el usuario se puede editar
    if not can_edit_user(user_obj, request.user):
        if user_obj.is_superuser:
            messages.error(
                request,
                f'No se puede editar al usuario "{user_obj.username}" porque es un superadministrador. Los superadministradores están protegidos.'
            )
        else:
            messages.error(
                request,
                'No tienes permisos para editar este usuario.'
            )
        return redirect('accounts:users_list')

    if request.method == 'POST':
        form = UserForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario actualizado exitosamente.')
            return redirect('accounts:users_list')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = UserForm(instance=user_obj)

    context = {
        'form': form,
        'user_obj': user_obj,
        'title': 'Editar Usuario',
        'action': 'Actualizar'
    }

    return render(request, 'accounts/users/form.html', context)


@login_required
@user_passes_test(is_admin)
def user_delete(request, pk):
    """Eliminar un usuario - CON PROTECCIÓN DE SUPERADMIN"""
    user_obj = get_object_or_404(User, pk=pk)

    # ✅ PROTECCIÓN: Verificar si el usuario se puede eliminar
    if not can_delete_user(user_obj, request.user):
        if user_obj.is_superuser:
            messages.error(
                request,
                f'No se puede eliminar al usuario "{user_obj.username}" porque es un superadministrador. Los superadministradores están protegidos.'
            )
        elif user_obj == request.user:
            messages.error(
                request,
                'No puedes eliminar tu propia cuenta.'
            )
        else:
            messages.error(
                request,
                'No tienes permisos para eliminar este usuario.'
            )
        return redirect('accounts:users_list')

    if request.method == 'POST':
        user_obj.delete()
        messages.success(request, 'Usuario eliminado exitosamente.')
        return redirect('accounts:users_list')

    context = {
        'user_obj': user_obj,
        'title': 'Eliminar Usuario',
    }

    return render(request, 'accounts/users/delete.html', context)


@login_required
@user_passes_test(is_admin)
def user_detail(request, pk):
    """Ver detalles de un usuario"""
    user_obj = get_object_or_404(User, pk=pk)

    # Obtener permisos del usuario
    permissions = user_obj.get_permissions() if hasattr(user_obj, 'get_permissions') else []

    context = {
        'user_obj': user_obj,
        'permissions': permissions,
        'title': f'Usuario: {user_obj.username}',
        'can_edit': can_edit_user(user_obj, request.user),
        'can_delete': can_delete_user(user_obj, request.user),
    }

    return render(request, 'accounts/users/detail.html', context)


# ============================================================
# VISTAS PARA CATEGORÍAS
# ============================================================
# AGREGAR ESTE IMPORT AL INICIO DE apps/accounts/views.py
from .forms import ModuleForm, RoleForm, UserForm, UserCreateForm, CategoryAdvancedForm


# REEMPLAZAR COMPLETAMENTE LAS VISTAS DE CATEGORÍAS

# ============================================================
# VISTAS PARA CATEGORÍAS - VERSIÓN AVANZADA CON GESTIÓN DE MÓDULOS
# ============================================================

@login_required
@permission_required('accounts.view_menucategory', raise_exception=True)
def categories_list(request):
    """Lista todas las categorías del menú"""
    categories = MenuCategory.objects.all().order_by('order', 'name')

    context = {
        'title': 'Categorías del Menú',
        'categories': categories,
    }
    return render(request, 'accounts/categories/list.html', context)


@login_required
@permission_required('accounts.view_menucategory', raise_exception=True)
def category_detail(request, pk):
    """Muestra detalles de una categoría"""
    category = get_object_or_404(MenuCategory, pk=pk)
    modules = category.get_modules()

    context = {
        'title': f'Categoría: {category.name}',
        'category': category,
        'modules': modules,
    }
    return render(request, 'accounts/categories/detail.html', context)


@login_required
@permission_required('accounts.add_menucategory', raise_exception=True)
def category_create(request):
    """Crea una nueva categoría con gestión de módulos"""
    if request.method == 'POST':
        form = CategoryAdvancedForm(request.POST)
        if form.is_valid():
            try:
                category = form.save()
                modules_count = category.get_modules().count()
                messages.success(
                    request,
                    f'Categoría "{category.name}" creada exitosamente con {modules_count} módulos asignados.'
                )
                return redirect('accounts:category_detail', pk=category.pk)
            except Exception as e:
                messages.error(request, f'Error al crear la categoría: {str(e)}')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = CategoryAdvancedForm()

    context = {
        'title': 'Crear Categoría',
        'form': form,
        'action': 'Crear',
    }
    return render(request, 'accounts/categories/form_advanced.html', context)


@login_required
@permission_required('accounts.change_menucategory', raise_exception=True)
def category_edit(request, pk):
    """Edita una categoría existente con gestión de módulos"""
    category = get_object_or_404(MenuCategory, pk=pk)

    if request.method == 'POST':
        form = CategoryAdvancedForm(request.POST, instance=category)
        if form.is_valid():
            try:
                old_modules_count = category.get_modules().count()
                updated_category = form.save()
                new_modules_count = updated_category.get_modules().count()

                # Mensaje personalizado basado en cambios
                if category.is_system and category.name == 'ADMINISTRACIÓN DEL SISTEMA':
                    messages.success(
                        request,
                        f'Categoría del sistema "{updated_category.name}" actualizada. Los módulos administrativos permanecen protegidos.'
                    )
                else:
                    messages.success(
                        request,
                        f'Categoría "{updated_category.name}" actualizada exitosamente. '
                        f'Módulos: {old_modules_count} → {new_modules_count}'
                    )
                return redirect('accounts:category_detail', pk=updated_category.pk)
            except Exception as e:
                messages.error(request, f'Error al actualizar la categoría: {str(e)}')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = CategoryAdvancedForm(instance=category)

    context = {
        'title': f'Editar Categoría: {category.name}',
        'form': form,
        'category': category,
        'action': 'Actualizar',
    }
    return render(request, 'accounts/categories/form_advanced.html', context)


@login_required
@permission_required('accounts.delete_menucategory', raise_exception=True)
def category_delete(request, pk):
    """Elimina una categoría con validaciones avanzadas"""
    category = get_object_or_404(MenuCategory, pk=pk)

    if request.method == 'POST':
        try:
            # ✅ VALIDACIÓN AVANZADA: Verificar múltiples condiciones
            if not category.can_be_deleted():
                modules = category.get_modules()
                if modules.exists():
                    # Verificar si algún módulo es crítico del sistema
                    system_modules = modules.filter(
                        name__in=[
                            'Gestión de Categorías',
                            'Gestión de Módulos',
                            'Gestión de Roles',
                            'Gestión de Usuarios'
                        ]
                    )

                    if system_modules.exists():
                        messages.error(
                            request,
                            f'No se puede eliminar la categoría "{category.name}" porque contiene módulos críticos del sistema: '
                            f'{", ".join([module.name for module in system_modules])}'
                        )
                    else:
                        messages.error(
                            request,
                            f'No se puede eliminar la categoría "{category.name}" porque tiene los siguientes módulos asignados: '
                            f'{", ".join([module.name for module in modules])}'
                        )
                else:
                    messages.error(
                        request,
                        f'No se puede eliminar la categoría "{category.name}" por restricciones del sistema.'
                    )
                return redirect('accounts:categories_list')

            # Protección adicional para categorías del sistema
            if category.is_system:
                messages.error(
                    request,
                    f'No se puede eliminar la categoría "{category.name}" porque es una categoría del sistema protegida.'
                )
                return redirect('accounts:categories_list')

            # Si llegamos aquí, se puede eliminar
            category_name = category.name
            category.delete()
            messages.success(request, f'Categoría "{category_name}" eliminada exitosamente.')
            return redirect('accounts:categories_list')

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('accounts:categories_list')
        except Exception as e:
            messages.error(request, f'Error inesperado al eliminar la categoría: {str(e)}')
            return redirect('accounts:categories_list')

    # Obtener información adicional para el template
    modules = category.get_modules()
    affected_roles = set()

    # Encontrar roles que serían afectados
    for module in modules:
        affected_roles.update(module.roles.all())

    context = {
        'title': f'Eliminar Categoría: {category.name}',
        'category': category,
        'modules': modules,
        'affected_roles': list(affected_roles),
        'modules_count': modules.count(),
        'affected_roles_count': len(affected_roles),
    }
    return render(request, 'accounts/categories/delete_advanced.html', context)


# ============================================================
# VISTAS PARA NAVEGACIÓN
# ============================================================

class NavigationForm(ModelForm):
    class Meta:
        model = Navigation
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'url': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'parent': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'group': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
        }


@login_required
@permission_required('accounts.view_navigation', raise_exception=True)
def navigation_list(request):
    """Lista todos los elementos de navegación"""
    navigation_items = Navigation.objects.select_related('group', 'category').order_by('category__order', 'order')

    context = {
        'title': 'Elementos del Menú',
        'navigation_items': navigation_items,
    }
    return render(request, 'accounts/navigation/list.html', context)


@login_required
@permission_required('accounts.view_navigation', raise_exception=True)
def navigation_detail(request, pk):
    """Muestra detalles de un elemento de navegación"""
    navigation = get_object_or_404(Navigation, pk=pk)

    context = {
        'title': f'Navegación: {navigation.name}',
        'navigation': navigation,
    }
    return render(request, 'accounts/navigation/detail.html', context)


@login_required
@permission_required('accounts.add_navigation', raise_exception=True)
def navigation_create(request):
    """Crea un nuevo elemento de navegación"""
    if request.method == 'POST':
        form = NavigationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Elemento de navegación creado exitosamente.')
            return redirect('accounts:navigation_list')
    else:
        form = NavigationForm()

    context = {
        'title': 'Crear Elemento de Navegación',
        'form': form,
        'action': 'Crear',
    }
    return render(request, 'accounts/navigation/form.html', context)


@login_required
@permission_required('accounts.change_navigation', raise_exception=True)
def navigation_edit(request, pk):
    """Edita un elemento de navegación existente"""
    navigation = get_object_or_404(Navigation, pk=pk)

    if request.method == 'POST':
        form = NavigationForm(request.POST, instance=navigation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Elemento de navegación actualizado exitosamente.')
            return redirect('accounts:navigation_detail', pk=navigation.pk)
    else:
        form = NavigationForm(instance=navigation)

    context = {
        'title': f'Editar Navegación: {navigation.name}',
        'form': form,
        'navigation': navigation,
        'action': 'Actualizar',
    }
    return render(request, 'accounts/navigation/form.html', context)


@login_required
@permission_required('accounts.delete_navigation', raise_exception=True)
def navigation_delete(request, pk):
    """Elimina un elemento de navegación"""
    navigation = get_object_or_404(Navigation, pk=pk)

    if request.method == 'POST':
        navigation.delete()
        messages.success(request, 'Elemento de navegación eliminado exitosamente.')
        return redirect('accounts:navigation_list')

    context = {
        'title': f'Eliminar Navegación: {navigation.name}',
        'navigation': navigation,
    }
    return render(request, 'accounts/navigation/delete.html', context)


# ============================================================
# VISTAS PARA ASIGNACIÓN DE MÓDULOS A ROLES
# ============================================================

@login_required
@permission_required('accounts.view_role', raise_exception=True)
def role_assignments(request):
    """Vista principal para gestionar asignaciones de módulos a roles"""
    roles = Role.objects.all().prefetch_related('groups')
    modules = Group.objects.all().order_by('name')

    context = {
        'title': 'Asignación de Módulos a Roles',
        'roles': roles,
        'modules': modules,
    }
    return render(request, 'accounts/assignments/list.html', context)


@login_required
@permission_required('accounts.change_role', raise_exception=True)
def role_assignment_detail(request, role_id):
    """Gestiona la asignación de módulos para un rol específico"""
    role = get_object_or_404(Role, pk=role_id)

    if request.method == 'POST':
        selected_modules = request.POST.getlist('modules')
        modules = Group.objects.filter(pk__in=selected_modules)
        role.groups.set(modules)

        messages.success(request, f'Módulos asignados al rol {role.name} exitosamente.')
        return redirect('accounts:role_assignments')

    all_modules = Group.objects.all().order_by('name')
    assigned_modules = role.groups.all()

    context = {
        'title': f'Asignar Módulos a: {role.name}',
        'role': role,
        'all_modules': all_modules,
        'assigned_modules': assigned_modules,
    }
    return render(request, 'accounts/assignments/detail.html', context)