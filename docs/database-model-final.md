# 🏗️ Modelado Final - CRM + WhatsApp Business

## 📊 Diagrama Mermaid - Versión Final Corregida

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
    
    %% Leads (SIMPLIFICADO - Solo prospección)
    Lead {
        id PK
        cliente_id FK
        inmueble_id FK
        origen string
        prioridad string
        interes_inicial text
        notas text
        fecha_primera_interaccion timestamp
        fecha_ultima_interaccion timestamp
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Conversaciones y Mensajes
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
    
    %% Tipos de Pago
    TipoPago {
        id PK
        nombre string
        descripcion text
        requiere_entidad_financiera boolean
        requiere_evaluacion_crediticia boolean
        dias_financiamiento int
        is_active boolean
        created_at timestamp
        updated_at timestamp
    }
    
    %% Proceso de Venta (CORREGIDO - Directo a Inmueble)
    ProcesoVenta {
        id PK
        inmueble_id FK
        cliente_id FK
        lead_id FK
        vendedor_id FK
        team_leader_id FK
        codigo_proceso string
        estado string
        etapa string
        fecha_inicio date
        fecha_cierre date
        valor_inmueble decimal
        valor_negociado decimal
        descuento decimal
        tipo_pago_id FK
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
    
    %% Venta Inmutable (NUEVO - Snapshot al cierre)
    VentaInmutable {
        id PK
        proceso_venta_id FK
        codigo_venta string
        fecha_venta date
        valor_final decimal
        descuento_aplicado decimal
        tipo_pago string
        entidad_financiera string
        cliente_snapshot text
        inmueble_snapshot text
        vendedor_snapshot text
        team_leader_snapshot text
        equipo_venta_snapshot text
        comisiones_snapshot text
        ponderadores_aplicados text
        precio_m2_momento decimal
        m2_inmueble decimal
        ubicacion_inmueble string
        created_at timestamp
        updated_at timestamp
    }
    
    %% Contrato (1:1 con VentaInmutable)
    Contrato {
        id PK
        venta_inmutable_id FK
        numero_contrato string
        fecha_firma date
        archivo_contrato string
        clausulas_especiales text
        observaciones text
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
    
    %% Asignaciones de Leads
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
    
    %% Citas y Reuniones
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
    %% RELACIONES - PROPUESTA NUEVA (FINAL)
    %% ==============================================
    
    %% Asignación de Vendedores a Clientes
    Vendedor ||--o{ Cliente : "assigned_to"
    TeamLeader ||--o{ Cliente : "manages"
    
    %% WhatsApp y Clientes
    Cliente ||--|| Conversacion : "has_one"
    Conversacion ||--o{ Mensaje : "contains"
    User ||--o{ Mensaje : "sends"
    
    %% Leads (SIMPLIFICADO)
    Cliente ||--o{ Lead : "generates"
    Inmueble ||--o{ Lead : "interests"
    
    %% Proceso de Venta (CORREGIDO)
    Inmueble ||--o{ ProcesoVenta : "sold_through"
    Cliente ||--o{ ProcesoVenta : "buys"
    Lead ||--o{ ProcesoVenta : "originates"
    Vendedor ||--o{ ProcesoVenta : "handles"
    TeamLeader ||--o{ ProcesoVenta : "supervises"
    TipoPago ||--o{ ProcesoVenta : "payment_method"
    
    %% Venta Inmutable (NUEVO)
    ProcesoVenta ||--|| VentaInmutable : "creates_snapshot"
    VentaInmutable ||--|| Contrato : "has_contract"
    
    %% Seguimiento
    ProcesoVenta ||--o{ SeguimientoLead : "tracked_by"
    ProcesoVenta ||--o{ Cita : "schedules"
    
    %% Múltiples Citas por Proceso
    Cita ||--o{ Cita : "follow_up"
    
    %% Asignaciones
    Lead ||--o{ AsignacionLead : "has"
    TeamLeader ||--o{ AsignacionLead : "receives"
    Vendedor ||--o{ AsignacionLead : "receives"
   
    %% Templates y Campañas
    WhatsAppTemplate ||--o{ CampañaMarketing : "uses"
    User ||--o{ WhatsAppTemplate : "creates"
    User ||--o{ CampañaMarketing : "creates"
    
    %% Seguimiento y Citas
    User ||--o{ SeguimientoLead : "performs"
    Lead ||--o{ SeguimientoLead : "tracked_by"
    Vendedor ||--o{ Cita : "schedules"
    Cliente ||--o{ Cita : "attends"
    Inmueble ||--o{ Cita : "shown"
```

## 🎯 **Cambios Finales Implementados**

### **1. Lead Simplificado (Solo Prospección)**
```sql
Lead {
    -- REMOVIDO: presupuesto_estimado, forma_pago_preferida, fecha_seguimiento
    -- MANTENIDO: Solo datos de prospección inicial
    origen string
    prioridad string
    interes_inicial text
    notas text
}
```

### **2. ProcesoVenta Conectado Directamente a Inmueble**
```sql
ProcesoVenta {
    inmueble_id FK           -- DIRECTO a inmueble
    cliente_id FK            -- Cliente comprador
    lead_id FK              -- OPCIONAL (puede ser NULL para contactos naturales)
    vendedor_id FK
    team_leader_id FK
    tipo_pago_id FK         -- FK a TipoPago
    valor_inmueble decimal  -- Precio original del inmueble
    valor_negociado decimal -- Precio final negociado
    descuento decimal       -- Descuento aplicado
}
```

### **3. VentaInmutable (Snapshot al Cierre)**
```sql
VentaInmutable {
    proceso_venta_id FK
    codigo_venta string
    fecha_venta date
    valor_final decimal
    -- SNAPSHOTS INMUTABLES
    cliente_snapshot text          -- JSON con datos del cliente
    inmueble_snapshot text         -- JSON con datos del inmueble
    vendedor_snapshot text         -- JSON con datos del vendedor
    team_leader_snapshot text      -- JSON con datos del team leader
    equipo_venta_snapshot text     -- JSON con datos del equipo
    comisiones_snapshot text       -- JSON con comisiones aplicadas
    ponderadores_aplicados text    -- JSON con ponderadores del momento
    precio_m2_momento decimal      -- Precio m2 en el momento de la venta
}
```

### **4. TipoPago (Formas de Pago)**
```sql
TipoPago {
    nombre string                       -- 'efectivo', 'credito_directo', 'credito_bancario', 'autofast'
    descripcion text
    requiere_entidad_financiera boolean
    requiere_evaluacion_crediticia boolean
    dias_financiamiento int
}
```

### **5. Contrato (1:1 con VentaInmutable)**
```sql
Contrato {
    venta_inmutable_id FK    -- 1:1 con VentaInmutable
    numero_contrato string
    fecha_firma date
    archivo_contrato string
    clausulas_especiales text
}
```

## ✅ **Casos de Uso Validados**

### **1. Venta por Lead de WhatsApp**
```
WhatsApp → Cliente → Lead → ProcesoVenta → VentaInmutable + Contrato
```

### **2. Venta por Contacto Natural**
```
Contacto Natural → Cliente → ProcesoVenta (sin Lead) → VentaInmutable + Contrato
```

### **3. Múltiples Leads → Una Venta**
```
Cliente con 3 Leads → Vendedor cierra 1 ProcesoVenta → VentaInmutable
```

### **4. Datos Inmutables**
```
Al cerrar venta → Snapshot de todo (vendedor, comisiones, ponderadores, etc.)
Si cambian comisiones mañana → Venta histórica mantiene datos originales
```

**¿Esta versión final cumple con todos los requisitos? ¿Procedemos con la implementación?**

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Corregir modelo: Lead sin datos de venta", "status": "completed", "priority": "high", "id": "1"}, {"content": "Crear tabla VentaInmutable con snapshot", "status": "completed", "priority": "high", "id": "2"}, {"content": "Conectar Inmueble directamente con ProcesoVenta", "status": "completed", "priority": "high", "id": "3"}, {"content": "Agregar tabla TipoPago", "status": "completed", "priority": "medium", "id": "4"}, {"content": "Permitir ProcesoVenta sin Lead", "status": "completed", "priority": "medium", "id": "5"}]