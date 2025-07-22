# 🏗️ Análisis de Modelado de Base de Datos - CRM + WhatsApp Business v2

## 📊 Diagrama Mermaid - Modelado Actual + Propuesta (REVISADO)

```mermaid
erDiagram
    %% ==============================================
    %% SISTEMA ACTUAL - Color Azul
    %% ==============================================
    
    %% Usuarios y Permisos
    User {
        id PK
        username string
        email string
        first_name string
        last_name string
        fecha_nacimiento date
        cedula string
        domicilio string
        latitud decimal
        longitud decimal
        role_id FK
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Role {
        id PK
        name string
        description text
        is_active boolean
        is_system boolean
        created_at timestamp
        updated_at timestamp
    }
    
    MenuCategory {
        id PK
        name string
        description text
        icon string
        color string
        order int
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Navigation {
        id PK
        group_id FK
        name string
        url string
        icon string
        order int
        category_id FK
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Jerarquía de Equipos de Venta
    EquipoVenta {
        id PK
        nombre string
        descripcion text
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    GerenteEquipo {
        id PK
        usuario_id FK
        equipo_venta_id FK
        activo boolean
        created_at timestamp
    }
    
    JefeVenta {
        id PK
        usuario_id FK
        gerente_equipo_id FK
        activo boolean
        created_at timestamp
    }
    
    TeamLeader {
        id PK
        usuario_id FK
        jefe_venta_id FK
        activo boolean
        created_at timestamp
    }
    
    Vendedor {
        id PK
        usuario_id FK
        team_leader_id FK
        activo boolean
        created_at timestamp
    }
    
    %% Proyectos Inmobiliarios
    Proyecto {
        id PK
        nombre string
        descripcion text
        tipo string
        estado string
        precio_base_m2 decimal
        gerente_proyecto_id FK
        jefe_proyecto_id FK
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    GerenteProyecto {
        id PK
        usuario_id FK
        activo boolean
        created_at timestamp
    }
    
    JefeProyecto {
        id PK
        usuario_id FK
        gerente_proyecto_id FK
        activo boolean
        created_at timestamp
    }
    
    Fase {
        id PK
        proyecto_id FK
        nombre string
        descripcion text
        numero_fase int
        precio_m2 decimal
        fecha_inicio_prevista date
        fecha_entrega_prevista date
        fecha_entrega_real date
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Inmueble {
        id PK
        fase_id FK
        piso_id FK
        manzana_id FK
        codigo string
        tipo string
        m2 decimal
        factor_precio decimal
        precio_manual decimal
        estado string
        caracteristicas text
        disponible boolean
        disponible_comercializacion boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Torre {
        id PK
        fase_id FK
        nombre string
        numero_torre int
        numero_pisos int
        descripcion text
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Piso {
        id PK
        torre_id FK
        numero_piso int
        nombre string
        descripcion text
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Sector {
        id PK
        fase_id FK
        nombre string
        numero_sector int
        descripcion text
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Manzana {
        id PK
        sector_id FK
        numero_manzana int
        nombre string
        descripcion text
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Ponderador {
        id PK
        proyecto_id FK
        fase_id FK
        nombre string
        tipo string
        nivel_aplicacion string
        porcentaje decimal
        monto_fijo decimal
        fecha_activacion timestamp
        fecha_desactivacion timestamp
        activo boolean
        version int
        ponderador_padre_id FK
        created_by_id FK
        activated_by_id FK
        deactivated_by_id FK
        created_at timestamp
        updated_at timestamp
    }
    
    ComisionVenta {
        id PK
        equipo_venta_id FK
        porcentaje_gerente_equipo decimal
        porcentaje_jefe_venta decimal
        porcentaje_team_leader decimal
        porcentaje_vendedor decimal
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    ComisionDesarrollo {
        id PK
        proyecto_id FK
        porcentaje_gerente_proyecto decimal
        porcentaje_jefe_proyecto decimal
        activo boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% ==============================================
    %% PROPUESTA NUEVA - Color Verde
    %% ==============================================
    
    %% Configuración WhatsApp Business
    WhatsAppConfig {
        id PK
        phone_number_id string
        business_account_id string
        access_token string
        app_secret string
        webhook_verify_token string
        webhook_url string
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Clientes/Contactos
    Cliente {
        id PK
        numero_whatsapp string
        nombre string
        apellido string
        email string
        cedula string
        fecha_nacimiento date
        domicilio string
        latitud decimal
        longitud decimal
        origen string
        etiquetas text
        vendedor_asignado_id FK
        team_leader_asignado_id FK
        fecha_primera_asignacion timestamp
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Leads
    Lead {
        id PK
        cliente_id FK
        inmueble_id FK
        origen string
        estado string
        prioridad string
        interes_inicial text
        presupuesto_estimado decimal
        forma_pago_preferida string
        fecha_seguimiento date
        notas text
        fecha_primera_interaccion timestamp
        fecha_ultima_interaccion timestamp
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Conversaciones y Mensajes (CORREGIDO - SIN N:N)
    Conversacion {
        id PK
        cliente_id FK
        numero_whatsapp string
        estado string
        ultimo_mensaje_at timestamp
        mensajes_no_leidos int
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    Mensaje {
        id PK
        conversacion_id FK
        whatsapp_message_id string
        tipo string
        direccion string
        contenido text
        media_url string
        media_type string
        estado string
        timestamp_whatsapp timestamp
        enviado_por_id FK
        leido_por_id FK
        fecha_lectura timestamp
        created_at timestamp
        updated_at timestamp
    }
    
    %% Proceso de Venta
    ProcesoVenta {
        id PK
        lead_id FK
        inmueble_id FK
        vendedor_id FK
        team_leader_id FK
        codigo_proceso string
        estado string
        etapa string
        fecha_inicio date
        fecha_cierre date
        valor_negociado decimal
        descuento decimal
        forma_pago string
        financiamiento_requerido boolean
        entidad_financiera string
        evaluacion_crediticia string
        fecha_evaluacion_credito date
        fecha_promesa_pago date
        fecha_firma_contrato date
        fecha_entrega_inmueble date
        observaciones text
        motivo_perdida text
        probabilidad_cierre decimal
        proxima_accion string
        fecha_proxima_accion date
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Historial de Seguimiento
    SeguimientoLead {
        id PK
        lead_id FK
        proceso_venta_id FK
        usuario_id FK
        tipo_actividad string
        descripcion text
        fecha_actividad timestamp
        resultado string
        proxima_accion string
        fecha_proxima_accion timestamp
        created_at timestamp
    }
    
    %% Asignaciones de Leads (SIMPLIFICADO)
    AsignacionLead {
        id PK
        lead_id FK
        team_leader_id FK
        vendedor_id FK
        tipo_asignacion string
        asignado_por_id FK
        fecha_asignacion timestamp
        fecha_reasignacion timestamp
        reasignado_por_id FK
        motivo_reasignacion text
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Citas y Reuniones (EXPANDIDO PARA MÚLTIPLES ENCUENTROS)
    Cita {
        id PK
        lead_id FK
        proceso_venta_id FK
        vendedor_id FK
        cliente_id FK
        inmueble_id FK
        tipo_cita string
        subtipo_cita string
        fecha_cita timestamp
        duracion_estimada int
        ubicacion string
        descripcion text
        estado string
        resultado string
        observaciones text
        recordatorio_enviado boolean
        fecha_recordatorio timestamp
        cita_padre_id FK
        numero_encuentro int
        created_at timestamp
        updated_at timestamp
    }
    
    %% Templates de WhatsApp
    WhatsAppTemplate {
        id PK
        name string
        category string
        language string
        status string
        components text
        created_by_id FK
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Campañas (futuro)
    CampañaMarketing {
        id PK
        nombre string
        descripcion text
        tipo string
        estado string
        template_id FK
        audiencia_objetivo text
        fecha_inicio date
        fecha_fin date
        presupuesto decimal
        created_by_id FK
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% ==============================================
    %% RELACIONES - SISTEMA ACTUAL
    %% ==============================================
    
    User ||--o{ Role : "has"
    Role ||--o{ Navigation : "grants_access"
    MenuCategory ||--o{ Navigation : "contains"
    
    %% Jerarquía de Equipos
    EquipoVenta ||--o{ GerenteEquipo : "has"
    GerenteEquipo ||--o{ JefeVenta : "manages"
    JefeVenta ||--o{ TeamLeader : "supervises"
    TeamLeader ||--o{ Vendedor : "leads"
    
    User ||--o{ GerenteEquipo : "is"
    User ||--o{ JefeVenta : "is"
    User ||--o{ TeamLeader : "is"
    User ||--o{ Vendedor : "is"
    
    %% Proyectos
    GerenteProyecto ||--o{ JefeProyecto : "manages"
    GerenteProyecto ||--o{ Proyecto : "leads"
    JefeProyecto ||--o{ Proyecto : "manages"
    
    User ||--o{ GerenteProyecto : "is"
    User ||--o{ JefeProyecto : "is"
    
    Proyecto ||--o{ Fase : "has"
    Fase ||--o{ Torre : "contains"
    Torre ||--o{ Piso : "has"
    Piso ||--o{ Inmueble : "contains"
    
    Fase ||--o{ Sector : "contains"
    Sector ||--o{ Manzana : "has"
    Manzana ||--o{ Inmueble : "contains"
    
    Proyecto ||--o{ Ponderador : "has"
    Fase ||--o{ Ponderador : "has"
    Inmueble ||--o{ Ponderador : "applies"
    
    EquipoVenta ||--|| ComisionVenta : "has"
    Proyecto ||--|| ComisionDesarrollo : "has"
    
    %% ==============================================
    %% RELACIONES - PROPUESTA NUEVA (CORREGIDAS)
    %% ==============================================
    
    %% Asignación de Vendedores a Clientes (NUEVO)
    Vendedor ||--o{ Cliente : "assigned_to"
    TeamLeader ||--o{ Cliente : "manages"
    
    %% WhatsApp y Clientes (SIMPLIFICADO)
    Cliente ||--|| Conversacion : "has_one"
    Conversacion ||--o{ Mensaje : "contains"
    User ||--o{ Mensaje : "sends"
    
    %% Leads (SIMPLIFICADO)
    Cliente ||--o{ Lead : "generates"
    Inmueble ||--o{ Lead : "interests"
    
    %% Proceso de Venta
    Lead ||--|| ProcesoVenta : "has"
    ProcesoVenta ||--o{ SeguimientoLead : "tracked_by"
    ProcesoVenta ||--o{ Cita : "schedules"
    
    %% Múltiples Citas por Proceso (NUEVO)
    Cita ||--o{ Cita : "follow_up"
    
    %% Asignaciones (SIMPLIFICADO)
    Lead ||--o{ AsignacionLead : "has"
    TeamLeader ||--o{ AsignacionLead : "receives"
    Vendedor ||--o{ AsignacionLead : "receives"
    
    %% Templates y Campañas
    WhatsAppTemplate ||--o{ CampañaMarketing : "uses"
    User ||--o{ WhatsAppTemplate : "creates"
    User ||--o{ CampañaMarketing : "creates"
    
    %% Seguimiento
    User ||--o{ SeguimientoLead : "performs"
    Lead ||--o{ SeguimientoLead : "tracked_by"
    
    %% Citas
    Vendedor ||--o{ Cita : "schedules"
    Cliente ||--o{ Cita : "attends"
    Inmueble ||--o{ Cita : "shown"
```

## 🎯 **Cambios Realizados - Versión 2**

### 🔧 **1. Eliminación de Relación N:N Problemática**

**ANTES:**
```
Conversacion N:M Lead (problemático)
```

**AHORA:**
```
Cliente 1:1 Conversacion (cada cliente tiene UNA conversación de WhatsApp)
Cliente 1:N Lead (un cliente puede tener múltiples leads)
```

### 🔧 **2. Asignación Unificada por Cliente**

**CAMBIO CLAVE:**
```sql
-- Tabla Cliente ahora tiene asignación directa
Cliente {
    vendedor_asignado_id FK    -- TODOS los leads del cliente van al mismo vendedor
    team_leader_asignado_id FK -- Team Leader que supervisa
    fecha_primera_asignacion timestamp
}
```

**BENEFICIOS:**
- ✅ **Integridad garantizada**: Todos los leads del mismo cliente → mismo vendedor
- ✅ **Simplicidad**: No más lógica compleja de asignación
- ✅ **Consistencia**: Un solo punto de asignación por cliente

### 🔧 **3. Múltiples Encuentros en Negociación**

**NUEVO MODELO DE CITAS:**
```sql
Cita {
    tipo_cita string         -- 'llamada', 'visita', 'reunion', 'cierre'
    subtipo_cita string      -- 'primera_llamada', 'seguimiento', 'visita_inmueble'
    cita_padre_id FK         -- Para crear cadenas de citas
    numero_encuentro int     -- 1, 2, 3... para ordenar
    resultado string         -- 'exitosa', 'reprogramar', 'sin_interes'
}
```

**TIPOS DE CITAS SOPORTADAS:**
- **Llamadas**: `primera_llamada`, `seguimiento_telefónico`, `confirmacion`
- **Visitas**: `visita_inmueble`, `visita_oficina`, `visita_proyecto`
- **Reuniones**: `reunion_negociacion`, `reunion_financiamiento`, `reunion_cierre`
- **Digitales**: `videollamada`, `presentacion_virtual`

### 🔧 **4. Flujo de Asignación Simplificado**

```
1. WhatsApp Webhook → Cliente creado
2. Cliente → Auto-asignación Vendedor (basado en Team Leader disponible)
3. Cliente → Todos los futuros Leads van al mismo Vendedor
4. Vendedor → Gestiona TODOS los leads del cliente
```

## 🚨 **Validaciones de Integridad**

### **Constraint Level (Base de Datos)**
```sql
-- Un cliente solo puede tener un vendedor asignado
ALTER TABLE Cliente ADD CONSTRAINT unique_client_assignment 
UNIQUE (vendedor_asignado_id, team_leader_asignado_id);

-- Un proceso de venta debe tener el mismo vendedor que el cliente
ALTER TABLE ProcesoVenta ADD CONSTRAINT fk_proceso_vendedor_cliente
FOREIGN KEY (vendedor_id) REFERENCES Cliente(vendedor_asignado_id);
```

### **Application Level (Django)**
```python
# En el modelo Cliente
def clean(self):
    if self.vendedor_asignado and self.team_leader_asignado:
        if self.vendedor_asignado.team_leader != self.team_leader_asignado:
            raise ValidationError("El vendedor debe pertenecer al team leader asignado")

# En el modelo Lead
def save(self, *args, **kwargs):
    # Heredar asignación del cliente
    if not self.vendedor_asignado:
        self.vendedor_asignado = self.cliente.vendedor_asignado
    super().save(*args, **kwargs)
```

## 🎯 **Casos de Uso Validados**

### **Caso 1: Nuevo Cliente por WhatsApp**
```
1. Mensaje WhatsApp → Cliente creado
2. Sistema asigna Team Leader disponible
3. Team Leader asigna Vendedor específico
4. Cliente.vendedor_asignado = Vendedor
5. Futuros Leads → Mismo vendedor automáticamente
```

### **Caso 2: Múltiples Leads del Mismo Cliente**
```
Cliente: Juan Pérez
├── Lead 1: Departamento Torre A → Vendedor: María
├── Lead 2: Terreno Sector B → Vendedor: María (mismo)
└── Lead 3: Local Comercial → Vendedor: María (mismo)
```

### **Caso 3: Proceso de Negociación con Múltiples Encuentros**
```
Proceso de Venta: Departamento 3A
├── Cita 1: Llamada inicial (exitosa)
├── Cita 2: Visita al inmueble (interesado)
├── Cita 3: Reunión negociación (en proceso)
├── Cita 4: Reunión financiamiento (pendiente)
└── Cita 5: Firma contrato (programada)
```

## ✅ **Validación Final**

¿Esta versión corregida resuelve tus preocupaciones sobre:
1. **Integridad**: ✅ Eliminada relación N:N problemática
2. **Asignación consistente**: ✅ Un cliente = un vendedor para todos sus leads
3. **Múltiples encuentros**: ✅ Soporte completo para diferentes tipos de citas
4. **Ubicación**: ✅ Archivo movido a `docs/`

¿Hay algo más que quieras ajustar antes de proceder con la implementación?