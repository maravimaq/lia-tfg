# LIA

Aplicación móvil Android desarrollada como Trabajo Fin de Grado (TFG).\
El proyecto consiste en una aplicación que sigue una arquitectura
**Modelo--Vista--Controlador (MVC)** y utiliza una estructura
**cliente-servidor híbrida**, donde la aplicación móvil consume
servicios proporcionados por un backend.

## Descripción del proyecto

El objetivo del proyecto es desarrollar una aplicación Android que
permita gestionar y visualizar información relacionada con compras,
productos, listas y analíticas asociadas.

La aplicación se comunicará con un servidor backend mediante una **API
REST**, lo que permitirá centralizar la lógica de negocio y el
almacenamiento de datos en una base de datos remota.

El sistema se compone de tres elementos principales:

-   **Aplicación Android** que actúa como cliente.
-   **Backend** que proporciona servicios mediante una API REST.
-   **Base de datos** donde se almacena la información persistente del
    sistema.

## Arquitectura

La aplicación sigue el patrón **Modelo--Vista--Controlador (MVC)**:

-   **Modelo**: gestiona los datos del sistema y su acceso.
-   **Vista**: representa la interfaz de usuario de la aplicación.
-   **Controlador**: coordina la interacción entre la vista y el modelo.

Además, el sistema sigue una arquitectura **híbrida cliente-servidor**,
en la que:

-   La aplicación Android gestiona la interfaz de usuario y parte de la
    lógica de interacción.
-   El backend gestiona la lógica de negocio y el acceso a la base de
    datos.
-   La comunicación entre ambos se realiza mediante una **API REST**.

## Tecnologías utilizadas

### Aplicación móvil (Frontend)
- React Native  
- Expo  
- TypeScript  
- Expo Router (navegación)  
- Componentes nativos de React Native  
- Axios / Fetch API (consumo de API REST)  
- React Hook Form (gestión de formularios)  
- Zod (validación de datos)  

### Backend
- Python  
- FastAPI  
- Pydantic  
- SQLAlchemy / SQLModel (acceso a base de datos)  
- Alembic (migraciones)  
- JWT (autenticación)  

### Base de datos
- PostgreSQL  

### Web Scraping
- Playwright  
- BeautifulSoup  

### Control de versiones
- Git  
- GitHub  

### Herramientas auxiliares
- Postman / Bruno (testing de API)  
- Docker (opcional para despliegue y entorno de desarrollo)  


## Estructura del repositorio

    LIA_TFG
    │
    ├─ android-app/      # Aplicación Android
    ├─ backend/          # API y lógica del servidor
    ├─ docs/             # Documentación técnica del proyecto
    ├─ scripts/          # Scripts auxiliares
    │
    ├─ docker-compose.yml
    ├─ README.md
    └─ .gitignore

## Metodología de desarrollo

El desarrollo del proyecto se realiza siguiendo un enfoque
**iterativo**, implementando funcionalidades de forma progresiva.

Estrategia de ramas:

-   `main` → versión estable del proyecto
-   `develop` → rama de integración
-   `feature/*` → nuevas funcionalidades
-   `fix/*` → corrección de errores

### Convención de commits

Formato utilizado:

    tipo: descripción breve del cambio

Tipos de commit:

-   feat → nueva funcionalidad
-   fix → corrección de error
-   docs → cambios en documentación
-   refactor → mejoras internas del código
-   test → pruebas
-   conf → configuración

Ejemplos:

    feat: crear pantalla de inicio de sesión
    fix: corregir validación de contraseña
    docs: añadir estructura MVC del proyecto
    conf: configurar proyecto Android en GitHub

## Autores

Proyecto desarrollado por los alumnos María del Mar Ávila Maqueda y Juan del Junco Obregón como parte del **Trabajo Fin de
Grado (TFG)**.

## Nota sobre el uso de herramientas de IA

Parte de la documentación del proyecto, incluyendo este archivo
`README.md`, ha sido redactada con la asistencia de herramientas de
**inteligencia artificial generativa (ChatGPT)** como apoyo en la
redacción y organización del contenido.

El uso de estas herramientas se ha limitado a la generación de texto
explicativo y no a la realización del desarrollo técnico del proyecto.

## Puesta en marcha del proyecto

### Requisitos previos

-   Python 3.10 o superior  
-   Node.js (para el frontend)  
-   Docker Desktop  
-   Git  
-   (Opcional) DBeaver

---

### Base de datos (PostgreSQL con Docker)

Levantar la base de datos:

```bash
docker compose up -d
```

Parar la base de datos:

```bash
docker compose down
```

Acceder a PostgreSQL:

```bash
docker exec -it lia_postgres psql -U postgres -d lia_db
```

### Backend (FastAPI)

Entrar en la carpeta "backend":

```bash
cd backend
```

Crear entorno virtual:

```bash
python -m venv .venv
```

Activar entorno virtual (Windows):

```bash
.venv\Scripts\activate
```

Activar entorno virtual (Windows):

```bash
pip install -r requirements.txt
```

Ejecutar servidor:

```bash
uvicorn app.main:app --reload
```

### Acceso a la API:

[Doc FastAPI](http://127.0.0.1:8000/docs)


### Frontend

#### 1. Requisitos previos

Antes de empezar, tener instalado:

- Node.js (recomendado versión LTS)
- npm (se instala junto con Node)
- Git
- Backend funcionando (FastAPI en puerto 8000)

##### Comprobar instalaciones

Ejecuta en terminal:

```bash
node -v
npm -v
git --version
```

---
#### 2. Inicializar el proyecto frontend

Desde la raíz del repositorio:

```bash
cd android-app
npx create-expo-app@latest . --template
```

Cuando pregunte plantilla:

Seleccionar: **blank (TypeScript)**

#### 3. Instalar dependencias necesarias

Dentro de `android-app`:

```bash
npm install axios react-hook-form zod @hookform/resolvers @react-native-async-storage/async-storage
npx expo install expo-router react-native-safe-area-context react-native-screens react-native-gesture-handler react-native-reanimated expo-linking expo-constants expo-status-bar
```

---
#### 4. Configuración obligatoria

##### 4.1 package.json

Abrir `android-app/package.json` y añadir/modificar:

```json
{
  "main": "expo-router/entry"
}
```

---
##### 4.2 babel.config.js

Crear archivo en `android-app/`:

```js
module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: ["react-native-reanimated/plugin"],
  };
};
```

---

##### 4.3 tsconfig.json

Editar o crear:

```json
{
  "extends": "expo/tsconfig.base",
  "compilerOptions": {
    "strict": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["*"]
    }
  }
}
```

#### 5. Configurar conexión con backend

Crear archivo:

📄 `android-app/src/utils/env.ts`

```ts
export const API_BASE_URL = "http://TU_IP_LOCAL:8000";
```
##### Cómo saber tu IP

En Windows:

```bash
ipconfig
```

Buscar:

 Dirección IPv4 → usar esa IP

---

##### Ejemplos

###### Móvil físico (Expo Go)

```ts
http://192.168.X.X:8000
```

###### Emulador Android

```ts
http://10.0.2.2:8000
```

---

#### 6. Ejecutar el frontend

Desde `android-app`:

```bash
npx expo start
```

---

#### 7. Orden correcto para ejecutar TODO el proyecto

##### 1. Base de datos

```bash
docker compose up -d
```

##### 2. Backend

```bash
cd backend
.venv\Scripts\activate
uvicorn app.main:app --reload
```

##### 3. Frontend

```bash
cd android-app
npx expo start
```

---

#### 8. Problemas comunes

##### No conecta con backend

Revisar IP en `env.ts`

##### Error de dependencias

Ejecutar:

```bash
npm install
```

##### Cambios no se reflejan

```bash
npx expo start -c
```

----
