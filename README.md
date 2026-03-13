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

### Aplicación Android

-   Android Studio
-   Java
-   XML (layouts)
-   Activities y Fragments
-   Material Design Components
-   RecyclerView
-   Retrofit
-   Gson
-   Room (SQLite)

### Backend

-   Python
-   FastAPI
-   psycopg2
-   JWT

### Base de datos

-   PostgreSQL

### Web Scraping

-   Playwright
-   BeautifulSoup

### Control de versiones

-   Git
-   GitHub

### Herramientas auxiliares

-   Postman
-   Docker (opcional)

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
