# API Auth Gateway 🚀

Un **API Gateway** basado en FastAPI que proporciona acceso autenticado a la API externa de inventario de activos. Actúa como un proxy seguro con **control de acceso basado en propiedad**, requiriendo autenticación JWT antes de reenviar solicitudes a la API de inventario externa.

## 🏗️ Arquitectura del Sistema

```mermaid
graph TB
    subgraph "Cliente"
        FE[Frontend/Cliente]
    end
    
    subgraph "API Gateway (FastAPI)"
        AUTH[🔐 Auth Router<br/>JWT Authentication]
        INV[📦 Inventory Router<br/>Protected Proxy]
        CORS[🌐 CORS Middleware]
        SENTRY[🚨 Sentry Integration]
    end
    
    subgraph "Base de Datos"
        PG[(🐘 PostgreSQL<br/>Railway)]
    end
    
    subgraph "API Externa"
        EXT[🏢 Inventory API<br/>inventoryapp.usbtopia.usbbog.edu.co]
    end
    
    subgraph "Monitoreo"
        SENT[📊 Sentry Dashboard]
    end
    
    FE -->|HTTP Requests| CORS
    CORS --> AUTH
    CORS --> INV
    
    AUTH <-->|User Data<br/>JWT Validation| PG
    INV -->|Ownership Check| PG
    INV -->|Filtered Requests<br/>httpx.AsyncClient| EXT
    
    AUTH --> SENTRY
    INV --> SENTRY
    SENTRY --> SENT
    
    classDef gateway fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef external fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef database fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef monitoring fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    
    class AUTH,INV,CORS gateway
    class EXT external
    class PG database
    class SENT,SENTRY monitoring
```

### 🔄 Flujo de Autenticación y Autorización

```mermaid
sequenceDiagram
    participant C as Cliente
    participant AG as API Gateway
    participant DB as PostgreSQL
    participant EXT as API Externa
    
    Note over C,EXT: 1. Autenticación
    C->>AG: POST /auth/login (credentials)
    AG->>DB: Validar usuario
    DB-->>AG: User data + dueno_de_activo
    AG-->>C: JWT Token
    
    Note over C,EXT: 2. Acceso a Inventario
    C->>AG: GET /inventario (with JWT)
    AG->>AG: Validar JWT
    AG->>DB: Obtener user info
    DB-->>AG: User + dueno_de_activo
    AG->>EXT: GET /inventario (proxy)
    EXT-->>AG: Raw inventory data
    AG->>AG: Filtrar por ownership<br/>(user.dueno_de_activo)
    AG-->>C: Filtered assets only
    
    Note over C,EXT: 3. Admin Access
    C->>AG: GET /inventario (admin JWT)
    AG->>AG: Check is_superuser=True
    AG->>EXT: GET /inventario
    EXT-->>AG: All inventory data
    AG-->>C: Complete dataset (no filter)
```

## 🎯 Características Principales

- **🔐 Autenticación JWT**: Sistema completo de autenticación con tokens de acceso y refresh
- **🏢 Control de Propiedad**: Los usuarios solo ven activos que poseen (`dueno_de_activo`)
- **👑 Acceso de Admin**: Los superusuarios pueden ver todos los activos
- **🔄 Proxy Inteligente**: Filtra datos antes de reenviar a la API externa
- **🚀 Despliegue en Railway**: Configuración automática de base de datos y puerto
- **📊 Monitoreo con Sentry**: Seguimiento de errores y rendimiento
- **⚡ Async/Await**: Arquitectura completamente asíncrona

## 🛠️ Stack Tecnológico

### Backend Core
- **FastAPI 0.116+**: Framework web moderno y rápido
- **SQLAlchemy 2.0**: ORM con soporte async y anotaciones `Mapped[type]`
- **PostgreSQL**: Base de datos principal (Railway)
- **httpx**: Cliente HTTP asíncrono para llamadas a API externa

### Autenticación & Seguridad
- **JWT**: Tokens de acceso y refresh
- **bcrypt**: Hashing seguro de contraseñas
- **HTTPBearer**: Esquema de seguridad FastAPI

### Despliegue & Monitoreo
- **Railway**: Plataforma de despliegue cloud
- **Sentry**: Monitoreo de errores y rendimiento
- **uvicorn**: Servidor ASGI de producción

## 🚀 Inicio Rápido

### Configuración del Entorno

```cmd
# Clonar el repositorio
git clone https://github.com/MiguelBonilla-sys/API_AUTH.git
cd API_AUTH

# Crear entorno virtual
python -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Variables de Entorno

Crear un archivo `.env` en la raíz del proyecto:

```env
# Base de datos (Railway auto-proporciona en producción)
DATABASE_URL=postgresql://user:password@localhost:5432/api_auth

# Autenticación JWT
JWT_SECRET_KEY=  # obligatorio: python -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API Externa
INVENTORY_API_BASE_URL=https://inventoryapp.usbtopia.usbbog.edu.co

# Monitoreo (opcional)
SENTRY_DSN=tu_sentry_dsn_url

# Railway (auto-detectado en producción)
PORT=8000
```

### Ejecutar la Aplicación

```cmd
# Desarrollo con auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# La aplicación estará disponible en http://localhost:8000
# Documentación interactiva en http://localhost:8000/docs
```

## 📁 Estructura del Proyecto

```
API_AUTH/
├── main.py                    # Aplicación FastAPI principal
├── requirements.txt           # Dependencias Python
├── Procfile                  # Configuración Railway
├── railway.toml              # Configuración Railway
├── docker-compose.yml        # Docker para desarrollo
├── Dockerfile               # Imagen Docker
│
├── src/
│   ├── auth/                 # Sistema de autenticación
│   │   ├── __init__.py
│   │   ├── dependencies.py   # Dependencias de seguridad
│   │   └── jwt_utils.py      # Utilidades JWT
│   │
│   ├── config/              # Configuración
│   │   ├── __init__.py
│   │   └── database.py      # Configuración SQLAlchemy
│   │
│   ├── models/              # Modelos de base de datos
│   │   ├── __init__.py
│   │   └── user.py          # Modelo de usuario
│   │
│   ├── routers/             # Rutas de la API
│   │   ├── __init__.py
│   │   ├── auth.py          # Endpoints de autenticación
│   │   └── inventory.py     # Proxy de inventario
│   │
│   └── schemas/             # Esquemas Pydantic
│       ├── __init__.py
│       ├── auth.py          # Esquemas de autenticación
│       └── inventory.py     # Esquemas de inventario
│
├── scripts/                 # Scripts de utilidades
│   ├── create_users.py      # Crear usuarios en lote
│   ├── upload_users_via_api.py  # Crear usuarios vía API
│   ├── generate_credentials.py  # Generar credenciales de prueba
│   └── setup_railway_db.py     # Configurar DB Railway
│
└── docs/                    # Documentación
    ├── RAILWAY_DEPLOY.md    # Guía de despliegue
    └── SISTEMA_PERMISOS.md  # Sistema de permisos
```

## 🔐 Sistema de Autenticación

### Endpoints de Autenticación

- `POST /auth/register`: Registrar nuevo usuario. Solo un superusuario autenticado puede crear administradores o asignar `dueno_de_activo`
- `POST /auth/login`: Iniciar sesión y obtener tokens
- `POST /auth/refresh`: Renovar token de acceso
- `GET /auth/me`: Obtener información del usuario actual

### Control de Acceso Basado en Propiedad

```python
# Los usuarios normales solo ven sus activos
if not current_user.is_superuser:
    filtered_assets = [
        asset for asset in all_assets 
        if asset.get("DUEÑO_DE_ACTIVO") == current_user.dueno_de_activo
    ]
else:
    # Los administradores ven todos los activos
    filtered_assets = all_assets
```

## � API de Inventario (Proxy)

Todos los endpoints de inventario requieren un token JWT válido:

```bash
# 1. Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "tu_usuario", "password": "tu_password"}'

# 2. Usar el token en las solicitudes
curl -X GET "http://localhost:8000/inventario/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## ⚙️ Variables de Entorno

```env
# Base de datos Railway
DATABASE_URL=postgresql://username:password@hostname:port/database

# JWT Configuration
JWT_SECRET_KEY=  # required, 32+ random characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# API Externa
INVENTORY_API_BASE_URL=https://inventoryapp.usbtopia.usbbog.edu.co

# Opcional
SENTRY_DSN=your-sentry-dsn
DEBUG=false
```

## 🏢 Deploy en Railway

1. Conectar repositorio a Railway
2. Agregar PostgreSQL add-on
3. Configurar variables de entorno
4. Railway auto-detectará el puerto desde `$PORT`

## 📁 Estructura del Proyecto

```
API_AUTH/
├── main.py                 # Aplicación FastAPI principal
├── requirements.txt        # Dependencias
├── .env.example           # Ejemplo de variables de entorno
├── src/
│   ├── auth/              # Sistema de autenticación
│   │   ├── jwt_utils.py   # Utilidades JWT
│   │   └── dependencies.py # Dependencias de auth
│   ├── config/            # Configuración
│   │   └── database.py    # Config de base de datos
│   ├── models/            # Modelos SQLAlchemy
│   │   └── user.py        # Modelo de usuario
│   ├── routers/           # Rutas de la API
│   │   ├── auth.py        # Rutas de autenticación
│   │   └── inventory.py   # Proxy a API de inventario
│   └── schemas/           # Esquemas Pydantic
│       ├── auth.py        # Esquemas de autenticación
│       └── inventory.py   # Esquemas de inventario
└── .github/
    └── copilot-instructions.md # Instrucciones para AI
```

## 🛡️ Seguridad

- Passwords hasheados con bcrypt
- Tokens JWT con expiración
- Validación de entrada con Pydantic
- Headers CORS configurados
- Manejo seguro de errores de API externa
- `JWT_SECRET_KEY` obligatorio (32+ caracteres aleatorios): la app no arranca sin él ni con valores de ejemplo
- Cuentas de prueba con contraseñas aleatorias por cuenta (`scripts/seed_passwords.py`); los archivos generados (`credentials/`, `scripts/user_credentials*.json`) están ignorados por git
- CI (`.github/workflows/security.yml`): gitleaks con reglas propias (`.gitleaks.toml`) y pruebas de configuración (`pytest`)

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## 📊 Monitoreo

- Integración con Sentry para tracking de errores
- Health checks en `/` y `/health`
- Logs estructurados para debugging

## 🔧 Desarrollo

Para contribuir al proyecto:

1. Fork del repositorio
2. Crear rama de feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit cambios: `git commit -am 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT.