# 🏗️ Análisis de Modelado de Base de Datos - CRM + WhatsApp Business

## 📊 Diagrama Mermaid - Modelado Actual + Propuesta

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
        team_leader_asignado_id FK
        vendedor_asignado_id FK
        fecha_asignacion_tl timestamp
        fecha_asignacion_vendedor timestamp
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
        lead_id FK
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
        fecha_cita timestamp
        duracion_estimada int
        ubicacion string
        descripcion text
        estado string
        recordatorio_enviado boolean
        fecha_recordatorio timestamp
        observaciones text
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
    %% RELACIONES - PROPUESTA NUEVA
    %% ==============================================
    
    %% WhatsApp y Clientes
    Cliente ||--o{ Conversacion : "has"
    Conversacion ||--o{ Mensaje : "contains"
    User ||--o{ Mensaje : "sends"
    
    %% Leads
    Cliente ||--o{ Lead : "generates"
    Inmueble ||--o{ Lead : "interests"
    TeamLeader ||--o{ Lead : "assigned_to"
    Vendedor ||--o{ Lead : "assigned_to"
    
    %% Proceso de Venta
    Lead ||--|| ProcesoVenta : "has"
    ProcesoVenta ||--o{ SeguimientoLead : "tracked_by"
    ProcesoVenta ||--o{ Cita : "schedules"
    
    %% Asignaciones
    Lead ||--o{ AsignacionLead : "has"
    TeamLeader ||--o{ AsignacionLead : "receives"
    Vendedor ||--o{ AsignacionLead : "receives"
    
    %% Conversaciones con Leads
    Conversacion ||--o{ Lead : "relates_to"
    
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

## 🎯 Análisis del Modelado Actual

### ✅ **Fortalezas Identificadas**

1. **Jerarquía de Equipos Bien Definida**
   - Estructura clara: GerenteEquipo → JefeVenta → TeamLeader → Vendedor
   - Separación correcta entre roles de ventas y desarrollo
   - Campos de auditoría apropiados

2. **Sistema de Proyectos Robusto**
   - Manejo flexible de terrenos y departamentos
   - Sistema de ponderadores sofisticado para precios
   - Estructura jerárquica (Proyecto → Fase → Torre/Sector → Piso/Manzana → Inmueble)

3. **Sistema de Permisos y Navegación**
   - Roles dinámicos con grupos
   - Navegación por categorías
   - Flexibilidad para agregar nuevos módulos

### ⚠️ **Áreas de Mejora Identificadas**

1. **Falta de Trazabilidad en Ventas**
   - No hay proceso formal de venta
   - Sin historial de seguimiento
   - Falta conexión entre leads y ventas

2. **Ausencia de Gestión de Clientes**
   - No hay entidad Cliente independiente
   - Falta información de contacto estructurada

3. **Sin Integración de Comunicaciones**
   - No manejo de WhatsApp Business
   - Sin historial de conversaciones

## 🚀 Propuesta de Nuevos Modelos

### 📱 **WhatsApp Business Integration**

#### **WhatsAppConfig**
- Configuración centralizada de credenciales
- Gestión de tokens y webhooks
- Soporte para múltiples números de negocio

#### **Cliente**
- Entidad independiente para gestión de contactos
- Información completa del cliente
- Geolocalización y segmentación

#### **Conversacion + Mensaje**
- Historial completo de comunicaciones
- Soporte para multimedia
- Estado de lectura y entrega

### 🎯 **Lead Management System**

#### **Lead**
- Conexión directa con Cliente e Inmueble
- Asignación automática a Team Leaders
- Priorización y seguimiento

#### **AsignacionLead**
- Historial completo de asignaciones
- Soporte para reasignaciones
- Trazabilidad de motivos

### 💼 **Proceso de Venta Completo**

#### **ProcesoVenta**
- Ciclo de vida completo de la venta
- Estados granulares (negociación, evaluación crediticia, etc.)
- Fechas clave y seguimiento

#### **SeguimientoLead**
- Historial detallado de actividades
- Próximas acciones programadas
- Resultados y observaciones

#### **Cita**
- Gestión de reuniones y visitas
- Recordatorios automáticos
- Seguimiento de resultados

## 🔗 Cardinalidades Críticas

### **1:N (Uno a Muchos)**
- `Cliente` → `Lead` (un cliente puede tener múltiples leads)
- `Cliente` → `Conversacion` (un cliente puede tener múltiples conversaciones)
- `Inmueble` → `Lead` (un inmueble puede generar múltiples leads)
- `TeamLeader` → `Lead` (un team leader puede tener múltiples leads)
- `Vendedor` → `Lead` (un vendedor puede tener múltiples leads)

### **1:1 (Uno a Uno)**
- `Lead` → `ProcesoVenta` (cada lead tiene un proceso de venta único)
- `Conversacion` → `Lead` (cada conversación principal se relaciona con un lead)

### **N:M (Muchos a Muchos)**
- `Lead` → `AsignacionLead` (un lead puede tener múltiples asignaciones en el tiempo)
- `Conversacion` → `Lead` (una conversación puede relacionarse con múltiples leads del mismo cliente)

## 🚨 Consideraciones Importantes

### **Flujo de Asignación de Leads**
1. **WhatsApp Webhook** → `Lead` creado automáticamente
2. **Auto-asignación** → `Team Leader` (basado en reglas)
3. **Asignación manual** → `Vendedor` (por el Team Leader)
4. **Proceso de Venta** → Seguimiento completo

### **Integridad Referencial**
- Soft deletes para mantener historial
- Constraints para evitar datos huérfanos
- Validaciones de estado en transiciones

### **Performance**
- Índices en campos de búsqueda frecuente
- Particionado por fechas para historiales
- Optimización para consultas de dashboard

¿Te parece correcta esta propuesta de modelado? ¿Hay alguna relación o entidad que quieras modificar antes de proceder con la implementación?