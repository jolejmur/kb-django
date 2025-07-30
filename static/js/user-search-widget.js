/**
 * Widget de búsqueda de usuarios con filtrado en tiempo real
 * y opción de crear nuevos usuarios sin cambiar de vista
 */
class UserSearchWidget {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            placeholder: 'Buscar usuario...',
            noResultsText: 'No se encontraron usuarios',
            createUserText: '+ Crear nuevo usuario',
            searchUrl: '/sales/ajax/search-users/',
            createUserUrl: '/sales/ajax/create-user/',
            minChars: 2,
            delay: 300,
            ...options
        };
        
        this.selectedUser = null;
        this.searchTimeout = null;
        this.isOpen = false;
        this.users = [];
        
        this.init();
    }
    
    init() {
        this.createHTML();
        this.attachEvents();
        this.loadInitialUsers();
    }
    
    createHTML() {
        this.container.innerHTML = `
            <div class="user-search-widget relative">
                <div class="search-input-container relative">
                    <input type="text" 
                           class="search-input w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500" 
                           placeholder="${this.options.placeholder}"
                           autocomplete="off">
                    <div class="absolute inset-y-0 right-0 flex items-center pr-3">
                        <i class="fas fa-search text-gray-400"></i>
                    </div>
                </div>
                
                <div class="dropdown-container absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg hidden max-h-64 overflow-y-auto">
                    <div class="loading-indicator p-4 text-center text-gray-500 hidden">
                        <i class="fas fa-spinner fa-spin mr-2"></i>
                        Buscando usuarios...
                    </div>
                    
                    <div class="user-list"></div>
                    
                    <div class="create-user-option border-t border-gray-200 p-3 hover:bg-blue-50 cursor-pointer text-blue-600">
                        <i class="fas fa-plus mr-2"></i>
                        ${this.options.createUserText}
                    </div>
                </div>
                
                <input type="hidden" name="usuario" class="selected-user-input">
            </div>
        `;
        
        this.searchInput = this.container.querySelector('.search-input');
        this.dropdown = this.container.querySelector('.dropdown-container');
        this.userList = this.container.querySelector('.user-list');
        this.loadingIndicator = this.container.querySelector('.loading-indicator');
        this.createUserOption = this.container.querySelector('.create-user-option');
        this.hiddenInput = this.container.querySelector('.selected-user-input');
    }
    
    attachEvents() {
        // Evento de búsqueda
        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            this.handleSearch(query);
        });
        
        // Eventos de foco
        this.searchInput.addEventListener('focus', () => {
            this.showDropdown();
        });
        
        // Cerrar al hacer click fuera
        document.addEventListener('click', (e) => {
            if (!this.container.contains(e.target)) {
                this.hideDropdown();
            }
        });
        
        // Crear nuevo usuario
        this.createUserOption.addEventListener('click', () => {
            this.openCreateUserModal();
        });
    }
    
    handleSearch(query) {
        clearTimeout(this.searchTimeout);
        
        if (query.length < this.options.minChars) {
            this.displayUsers(this.users);
            return;
        }
        
        this.searchTimeout = setTimeout(() => {
            this.searchUsers(query);
        }, this.options.delay);
    }
    
    async searchUsers(query) {
        this.showLoading();
        
        try {
            const response = await fetch(`${this.options.searchUrl}?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayUsers(data.users);
            } else {
                this.showError(data.message || 'Error al buscar usuarios');
            }
        } catch (error) {
            console.error('Error searching users:', error);
            this.showError('Error de conexión al buscar usuarios');
        } finally {
            this.hideLoading();
        }
    }
    
    async loadInitialUsers() {
        try {
            const response = await fetch(this.options.searchUrl);
            const data = await response.json();
            
            if (data.success) {
                this.users = data.users;
                this.displayUsers(this.users);
            }
        } catch (error) {
            console.error('Error loading initial users:', error);
        }
    }
    
    displayUsers(users) {
        this.userList.innerHTML = '';
        
        if (users.length === 0) {
            this.userList.innerHTML = `
                <div class="p-4 text-center text-gray-500">
                    <i class="fas fa-user-slash mr-2"></i>
                    ${this.options.noResultsText}
                </div>
            `;
            return;
        }
        
        users.forEach(user => {
            const userItem = document.createElement('div');
            userItem.className = 'user-item p-3 hover:bg-gray-50 cursor-pointer border-b border-gray-100 last:border-b-0';
            userItem.innerHTML = `
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <i class="fas fa-user text-blue-600 text-sm"></i>
                        </div>
                    </div>
                    <div class="ml-3 flex-1">
                        <p class="text-sm font-medium text-gray-900">${user.full_name || user.username}</p>
                        <p class="text-xs text-gray-500">${user.email}</p>
                    </div>
                </div>
            `;
            
            userItem.addEventListener('click', () => {
                this.selectUser(user);
            });
            
            this.userList.appendChild(userItem);
        });
    }
    
    selectUser(user) {
        this.selectedUser = user;
        this.searchInput.value = user.full_name || user.username;
        this.hiddenInput.value = user.id;
        this.hideDropdown();
        
        // Disparar evento personalizado
        this.container.dispatchEvent(new CustomEvent('userSelected', {
            detail: { user: user }
        }));
    }
    
    showDropdown() {
        this.dropdown.classList.remove('hidden');
        this.isOpen = true;
    }
    
    hideDropdown() {
        this.dropdown.classList.add('hidden');
        this.isOpen = false;
    }
    
    showLoading() {
        this.loadingIndicator.classList.remove('hidden');
        this.userList.classList.add('hidden');
    }
    
    hideLoading() {
        this.loadingIndicator.classList.add('hidden');
        this.userList.classList.remove('hidden');
    }
    
    showError(message) {
        this.userList.innerHTML = `
            <div class="p-4 text-center text-red-500">
                <i class="fas fa-exclamation-triangle mr-2"></i>
                ${message}
            </div>
        `;
    }
    
    openCreateUserModal() {
        const modal = new CreateUserModal({
            onUserCreated: (user) => {
                this.users.unshift(user);
                this.selectUser(user);
                this.displayUsers(this.users);
            }
        });
        modal.show();
    }
    
    // Métodos públicos
    getValue() {
        return this.selectedUser ? this.selectedUser.id : null;
    }
    
    getSelectedUser() {
        return this.selectedUser;
    }
    
    setValue(userId, userName) {
        this.hiddenInput.value = userId;
        this.searchInput.value = userName;
        this.selectedUser = { id: userId, full_name: userName };
    }
    
    clear() {
        this.selectedUser = null;
        this.searchInput.value = '';
        this.hiddenInput.value = '';
        this.hideDropdown();
    }
}

/**
 * Modal para crear nuevos usuarios
 */
class CreateUserModal {
    constructor(options = {}) {
        this.options = {
            createUrl: '/sales/ajax/create-user/',
            onUserCreated: () => {},
            ...options
        };
        
        this.modal = null;
        this.form = null;
        this.createHTML();
        this.attachEvents();
    }
    
    createHTML() {
        const modalHTML = `
            <div class="create-user-modal fixed inset-0 z-50 hidden overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
                <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
                    <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>
                    
                    <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
                    
                    <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
                        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                            <div class="sm:flex sm:items-start">
                                <div class="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-blue-100 sm:mx-0 sm:h-10 sm:w-10">
                                    <i class="fas fa-user-plus text-blue-600"></i>
                                </div>
                                <div class="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                                    <h3 class="text-lg leading-6 font-medium text-gray-900" id="modal-title">
                                        Crear Nuevo Usuario
                                    </h3>
                                    <div class="mt-4">
                                        <form class="create-user-form space-y-4">
                                            <!-- Información básica -->
                                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">
                                                        Nombre <span class="text-red-500">*</span>
                                                    </label>
                                                    <input type="text" name="first_name" required
                                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                                </div>
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">
                                                        Apellido <span class="text-red-500">*</span>
                                                    </label>
                                                    <input type="text" name="last_name" required
                                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                                </div>
                                            </div>
                                            
                                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">
                                                        Email <span class="text-red-500">*</span>
                                                    </label>
                                                    <input type="email" name="email" required
                                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                                </div>
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">
                                                        Usuario <span class="text-red-500">*</span>
                                                    </label>
                                                    <input type="text" name="username" required
                                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                                    <p class="text-xs text-gray-500 mt-1">Solo letras, números y guiones bajos</p>
                                                </div>
                                            </div>
                                            
                                            <!-- Información personal -->
                                            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">
                                                        Cédula de Identidad
                                                    </label>
                                                    <input type="text" name="cedula"
                                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                                           placeholder="Ej: 12345678-9">
                                                </div>
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">
                                                        Fecha de Nacimiento
                                                    </label>
                                                    <input type="date" name="fecha_nacimiento"
                                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                                </div>
                                            </div>
                                            
                                            <div>
                                                <label class="block text-sm font-medium text-gray-700 mb-1">
                                                    Domicilio
                                                </label>
                                                <input type="text" name="domicilio"
                                                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                                       placeholder="Dirección completa del domicilio">
                                            </div>
                                            
                                            <!-- Coordenadas geográficas -->
                                            <div>
                                                <label class="block text-sm font-medium text-gray-700 mb-1">
                                                    Ubicación Geográfica
                                                </label>
                                                <div class="space-y-2">
                                                    <div class="relative">
                                                        <button type="button" class="location-btn w-full px-3 py-2 border border-gray-300 rounded-md text-left focus:ring-2 focus:ring-blue-500 focus:border-blue-500 hover:bg-gray-50">
                                                            <i class="fas fa-map-marker-alt mr-2 text-blue-600"></i>
                                                            <span class="location-text">Seleccionar ubicación en el mapa</span>
                                                        </button>
                                                        <input type="hidden" name="latitud" class="latitud-input">
                                                        <input type="hidden" name="longitud" class="longitud-input">
                                                    </div>
                                                    <div class="coordinates-display hidden bg-blue-50 p-2 rounded text-sm text-blue-700">
                                                        <i class="fas fa-map-marker-alt mr-1"></i>
                                                        <span class="coordinates-text"></span>
                                                    </div>
                                                </div>
                                                <p class="text-xs text-gray-500 mt-1">Opcional: Selecciona la ubicación del domicilio</p>
                                            </div>
                                            
                                            <!-- Contraseña -->
                                            <div>
                                                <label class="block text-sm font-medium text-gray-700 mb-1">
                                                    Contraseña Temporal <span class="text-red-500">*</span>
                                                </label>
                                                <input type="password" name="password" required
                                                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
                                                <p class="text-xs text-gray-500 mt-1">El usuario deberá cambiarla en su primer ingreso</p>
                                            </div>
                                            
                                            <div class="error-messages hidden bg-red-50 border border-red-200 rounded-md p-3">
                                                <div class="error-content text-sm text-red-600"></div>
                                            </div>
                                        </form>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                            <button type="button" class="create-btn w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm">
                                <i class="fas fa-user-plus mr-2"></i>
                                Crear Usuario
                            </button>
                            <button type="button" class="cancel-btn mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm">
                                Cancelar
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.querySelector('.create-user-modal');
        this.form = this.modal.querySelector('.create-user-form');
        this.errorContainer = this.modal.querySelector('.error-messages');
        this.errorContent = this.modal.querySelector('.error-content');
    }
    
    attachEvents() {
        // Botón crear
        this.modal.querySelector('.create-btn').addEventListener('click', () => {
            this.createUser();
        });
        
        // Botón cancelar
        this.modal.querySelector('.cancel-btn').addEventListener('click', () => {
            this.hide();
        });
        
        // Cerrar al hacer click en el overlay
        this.modal.querySelector('.bg-gray-500').addEventListener('click', () => {
            this.hide();
        });
        
        // Envío del formulario
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.createUser();
        });
        
        // Auto-generar username basado en nombre y apellido
        const firstNameInput = this.form.querySelector('[name="first_name"]');
        const lastNameInput = this.form.querySelector('[name="last_name"]');
        const usernameInput = this.form.querySelector('[name="username"]');
        
        [firstNameInput, lastNameInput].forEach(input => {
            input.addEventListener('input', () => {
                if (!usernameInput.value || usernameInput.hasAttribute('data-auto-generated')) {
                    const firstName = firstNameInput.value.trim().toLowerCase();
                    const lastName = lastNameInput.value.trim().toLowerCase();
                    if (firstName && lastName) {
                        // Tomar primera letra del nombre y primer apellido (hasta el primer espacio)
                        const firstLetter = firstName.charAt(0);
                        const firstLastName = lastName.split(' ')[0]; // Solo hasta el primer espacio
                        usernameInput.value = `${firstLetter}${firstLastName}`.replace(/[^a-z0-9._]/g, '');
                        usernameInput.setAttribute('data-auto-generated', 'true');
                    }
                }
            });
        });
        
        usernameInput.addEventListener('input', () => {
            usernameInput.removeAttribute('data-auto-generated');
        });
        
        // Selector de ubicación geográfica
        const locationBtn = this.modal.querySelector('.location-btn');
        const locationText = this.modal.querySelector('.location-text');
        const coordinatesDisplay = this.modal.querySelector('.coordinates-display');
        const coordinatesText = this.modal.querySelector('.coordinates-text');
        const latitudInput = this.modal.querySelector('.latitud-input');
        const longitudInput = this.modal.querySelector('.longitud-input');
        
        locationBtn.addEventListener('click', () => {
            this.openLocationSelector((lat, lng) => {
                latitudInput.value = lat;
                longitudInput.value = lng;
                locationText.textContent = `Ubicación seleccionada`;
                coordinatesText.textContent = `Lat: ${lat.toFixed(6)}, Lng: ${lng.toFixed(6)}`;
                coordinatesDisplay.classList.remove('hidden');
            });
        });
    }
    
    openLocationSelector(callback) {
        const locationModal = new LocationSelectorModal({
            onLocationSelected: callback
        });
        locationModal.show();
    }
    
    async createUser() {
        const formData = new FormData(this.form);
        const createBtn = this.modal.querySelector('.create-btn');
        const originalText = createBtn.innerHTML;
        
        // Mostrar loading
        createBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Creando...';
        createBtn.disabled = true;
        this.hideError();
        
        try {
            const response = await fetch(this.options.createUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.options.onUserCreated(data.user);
                this.hide();
                this.showSuccessMessage(data.message || 'Usuario creado exitosamente');
            } else {
                this.showError(data.errors || data.message || 'Error al crear el usuario');
            }
        } catch (error) {
            console.error('Error creating user:', error);
            this.showError('Error de conexión al crear el usuario');
        } finally {
            createBtn.innerHTML = originalText;
            createBtn.disabled = false;
        }
    }
    
    show() {
        this.modal.classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
        
        // Foco en el primer campo
        setTimeout(() => {
            this.form.querySelector('input').focus();
        }, 100);
    }
    
    hide() {
        this.modal.classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        this.form.reset();
        this.hideError();
    }
    
    showError(errors) {
        let errorHTML = '';
        
        if (typeof errors === 'string') {
            errorHTML = errors;
        } else if (typeof errors === 'object') {
            errorHTML = Object.values(errors).flat().join('<br>');
        }
        
        this.errorContent.innerHTML = errorHTML;
        this.errorContainer.classList.remove('hidden');
    }
    
    hideError() {
        this.errorContainer.classList.add('hidden');
    }
    
    showSuccessMessage(message) {
        // Crear notificación temporal
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 z-50 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg';
        notification.innerHTML = `
            <div class="flex items-center">
                <i class="fas fa-check-circle mr-2"></i>
                ${message}
            </div>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
    
    destroy() {
        if (this.modal) {
            this.modal.remove();
        }
    }
}

/**
 * Modal para seleccionar ubicación geográfica
 */
class LocationSelectorModal {
    constructor(options = {}) {
        this.options = {
            onLocationSelected: () => {},
            defaultLat: -17.8146,  // Santa Cruz, Bolivia
            defaultLng: -63.1560,
            ...options
        };
        
        this.modal = null;
        this.map = null;
        this.marker = null;
        this.selectedCoordinates = null;
        this.resizeObserver = null;
        
        this.createHTML();
        this.attachEvents();
    }
    
    createHTML() {
        const modalHTML = `
            <div class="location-selector-modal fixed inset-0 z-50 hidden flex items-start justify-center pt-12 p-4" aria-labelledby="location-modal-title" role="dialog" aria-modal="true">
                <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" aria-hidden="true"></div>
                
                <div class="relative bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[85vh] flex flex-col">
                    <!-- Header compacto -->
                    <div class="flex items-center justify-between p-4 border-b border-gray-200">
                        <div class="flex items-center">
                            <div class="flex-shrink-0 flex items-center justify-center h-8 w-8 rounded-full bg-blue-100 mr-3">
                                <i class="fas fa-map-marker-alt text-blue-600 text-sm"></i>
                            </div>
                            <h3 class="text-lg font-medium text-gray-900" id="location-modal-title">
                                Seleccionar Ubicación
                            </h3>
                        </div>
                        <button type="button" class="cancel-location-btn text-gray-400 hover:text-gray-600">
                            <i class="fas fa-times text-xl"></i>
                        </button>
                    </div>
                    
                    <!-- Contenido del mapa - ocupa el espacio disponible -->
                    <div class="flex-1 p-4 min-h-0">
                        <p class="text-sm text-gray-600 mb-3">
                            Haz clic en el mapa para seleccionar la ubicación del domicilio
                        </p>
                        
                        <div class="map-container h-full min-h-[400px]">
                            <div id="location-map" class="w-full h-full border border-gray-300 rounded-lg"></div>
                        </div>
                        
                        <div class="mt-3 coordinates-info hidden bg-blue-50 p-3 rounded-lg">
                            <div class="flex items-center">
                                <i class="fas fa-map-marker-alt text-blue-600 mr-2"></i>
                                <div>
                                    <p class="text-sm font-medium text-blue-900">Ubicación seleccionada</p>
                                    <p class="text-sm text-blue-700 coordinates-display-text"></p>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Footer con botones -->
                    <div class="flex justify-end space-x-3 p-4 border-t border-gray-200">
                        <button type="button" class="cancel-location-btn px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                            Cancelar
                        </button>
                        <button type="button" class="confirm-location-btn px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500" disabled>
                            <i class="fas fa-check mr-2"></i>
                            Confirmar Ubicación
                        </button>
                    </div>
                </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.querySelector('.location-selector-modal');
        this.coordinatesInfo = this.modal.querySelector('.coordinates-info');
        this.coordinatesDisplayText = this.modal.querySelector('.coordinates-display-text');
        this.confirmBtn = this.modal.querySelector('.confirm-location-btn');
    }
    
    attachEvents() {
        // Botón confirmar
        this.confirmBtn.addEventListener('click', () => {
            if (this.selectedCoordinates) {
                this.options.onLocationSelected(this.selectedCoordinates.lat, this.selectedCoordinates.lng);
                this.hide();
            }
        });
        
        // Botones cancelar (hay dos en el nuevo HTML)
        this.modal.querySelectorAll('.cancel-location-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.hide();
            });
        });
        
        // Cerrar al hacer click en el overlay
        this.modal.querySelector('.bg-gray-500').addEventListener('click', () => {
            this.hide();
        });
    }
    
    show() {
        this.modal.classList.remove('hidden');
        this.modal.style.display = 'flex'; // Asegurar que use flexbox
        document.body.classList.add('overflow-hidden');
        
        // Inicializar el mapa después de mostrar el modal
        setTimeout(() => {
            this.initializeMap();
        }, 100);
    }
    
    hide() {
        this.modal.classList.add('hidden');
        this.modal.style.display = 'none'; // Ocultar completamente
        document.body.classList.remove('overflow-hidden');
    }
    
    initializeMap() {
        console.log('🗺️ Iniciando mapa...');
        
        // Verificar si Leaflet está disponible
        if (typeof L === 'undefined') {
            console.error('❌ Leaflet no está disponible');
            this.showFallbackInput();
            return;
        }
        
        // Esperar un poco más en móviles para que el DOM esté listo
        const isMobile = window.innerWidth < 768;
        const delay = isMobile ? 300 : 100;
        
        setTimeout(() => {
            try {
                // Asegurar que el contenedor del mapa tenga dimensiones
                const mapContainer = document.getElementById('location-map');
                if (!mapContainer) {
                    console.error('❌ Contenedor del mapa no encontrado');
                    this.showFallbackInput();
                    return;
                }
                
                console.log('📏 Configurando dimensiones del contenedor...');
                
                // Forzar que el contenedor tenga altura antes de inicializar
                if (isMobile) {
                    // En móviles, usar altura fija más pequeña
                    mapContainer.style.height = '300px';
                    mapContainer.style.minHeight = '300px';
                } else {
                    // En desktop, usar altura completa
                    mapContainer.style.height = '100%';
                    mapContainer.style.minHeight = '400px';
                }
                mapContainer.style.width = '100%';
                mapContainer.style.display = 'block';
                
                console.log(`📱 Modo: ${isMobile ? 'Móvil' : 'Desktop'}, Altura: ${mapContainer.style.height}`);
            
                console.log('🗺️ Creando instancia del mapa...');
                
                // Crear el mapa con configuración optimizada para móviles
                this.map = L.map('location-map', {
                    zoomControl: !isMobile, // Sin controles de zoom en móvil
                    scrollWheelZoom: !isMobile, // Sin scroll zoom en móvil
                    doubleClickZoom: true,
                    boxZoom: !isMobile,
                    keyboard: !isMobile,
                    dragging: true,
                    touchZoom: isMobile, // Habilitar zoom táctil en móvil
                    // Configuración específica para modales
                    fadeAnimation: false,
                    zoomAnimation: false,
                    markerZoomAnimation: false
                }).setView([this.options.defaultLat, this.options.defaultLng], isMobile ? 12 : 13);
                
                console.log('✅ Mapa creado exitosamente');
                
                // Agregar capa de OpenStreetMap con timeout para evitar errores de red
                const tileLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '© OpenStreetMap contributors',
                    maxZoom: 19,
                    timeout: 10000 // 10 segundos de timeout
                });
                
                tileLayer.on('tileerror', (e) => {
                    console.warn('⚠️ Error cargando tile del mapa:', e);
                });
                
                tileLayer.addTo(this.map);
                
                // Invalidar el tamaño del mapa después de varios delays
                const invalidateSizes = [250, 500, 1000];
                invalidateSizes.forEach(delay => {
                    setTimeout(() => {
                        if (this.map) {
                            console.log(`🔄 Invalidando tamaño del mapa (${delay}ms)`);
                            this.map.invalidateSize();
                        }
                    }, delay);
                });
                
                // Observer para cambios de tamaño del modal
                if (window.ResizeObserver && !isMobile) {
                    this.resizeObserver = new ResizeObserver(() => {
                        if (this.map) {
                            this.map.invalidateSize();
                        }
                    });
                    this.resizeObserver.observe(mapContainer);
                }
                
                // Agregar evento de clic
                this.map.on('click', (e) => {
                    console.log('📍 Click en mapa:', e.latlng);
                    this.setLocation(e.latlng.lat, e.latlng.lng);
                });
                
                // Intentar obtener la ubicación actual del usuario (opcional en móvil)
                if (navigator.geolocation && !isMobile) {
                    navigator.geolocation.getCurrentPosition((position) => {
                        const lat = position.coords.latitude;
                        const lng = position.coords.longitude;
                        console.log('📍 Ubicación actual obtenida:', lat, lng);
                        this.map.setView([lat, lng], 15);
                        setTimeout(() => {
                            if (this.map) {
                                this.map.invalidateSize();
                            }
                        }, 100);
                    }, (error) => {
                        console.log('⚠️ No se pudo obtener la ubicación actual:', error);
                    });
                }
                
                console.log('✅ Mapa inicializado completamente');
                
            } catch (error) {
                console.error('❌ Error al inicializar el mapa:', error);
                this.showFallbackInput();
            }
        }, delay);
    }
    
    setLocation(lat, lng) {
        // Remover marcador anterior si existe
        if (this.marker) {
            this.map.removeLayer(this.marker);
        }
        
        // Agregar nuevo marcador
        this.marker = L.marker([lat, lng]).addTo(this.map);
        
        // Guardar coordenadas
        this.selectedCoordinates = { lat, lng };
        
        // Mostrar información de coordenadas
        this.coordinatesDisplayText.textContent = `Latitud: ${lat.toFixed(6)}, Longitud: ${lng.toFixed(6)}`;
        this.coordinatesInfo.classList.remove('hidden');
        
        // Habilitar botón de confirmación
        this.confirmBtn.disabled = false;
    }
    
    showFallbackInput() {
        // Mostrar input manual si no está disponible el mapa
        const mapContainer = this.modal.querySelector('.map-container');
        mapContainer.innerHTML = `
            <div class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div class="flex items-center mb-3">
                    <i class="fas fa-exclamation-triangle text-yellow-600 mr-2"></i>
                    <p class="text-sm text-yellow-800">No se pudo cargar el mapa. Ingresa las coordenadas manualmente:</p>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Latitud</label>
                        <input type="number" class="manual-lat w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500" 
                               step="0.000001" placeholder="Ej: -17.814611">
                    </div>
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-1">Longitud</label>
                        <input type="number" class="manual-lng w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500" 
                               step="0.000001" placeholder="Ej: -63.156013">
                    </div>
                </div>
            </div>
        `;
        
        // Agregar eventos a los inputs manuales
        const latInput = mapContainer.querySelector('.manual-lat');
        const lngInput = mapContainer.querySelector('.manual-lng');
        
        [latInput, lngInput].forEach(input => {
            input.addEventListener('input', () => {
                const lat = parseFloat(latInput.value);
                const lng = parseFloat(lngInput.value);
                
                if (!isNaN(lat) && !isNaN(lng)) {
                    this.selectedCoordinates = { lat, lng };
                    this.coordinatesDisplayText.textContent = `Latitud: ${lat.toFixed(6)}, Longitud: ${lng.toFixed(6)}`;
                    this.coordinatesInfo.classList.remove('hidden');
                    this.confirmBtn.disabled = false;
                } else {
                    this.selectedCoordinates = null;
                    this.coordinatesInfo.classList.add('hidden');
                    this.confirmBtn.disabled = true;
                }
            });
        });
    }
    
    destroy() {
        // Limpiar observer
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
            this.resizeObserver = null;
        }
        
        // Limpiar mapa
        if (this.map) {
            this.map.remove();
            this.map = null;
        }
        
        if (this.modal) {
            this.modal.remove();
        }
    }
}