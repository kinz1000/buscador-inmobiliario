# 🏠 Buscador Inmobiliario

Sistema de automatización de alertas inmobiliarias desarrollado en Python.

El proyecto centraliza alertas recibidas por correo desde varios portales inmobiliarios, normaliza la información, filtra por zonas, evita duplicados, identifica el anunciante cuando es posible y envía un resumen consolidado con los anuncios relevantes.

Actualmente trabaja con:

- Idealista
- Fotocasa
- Habitaclia
- Pisos.com
- Milanuncios

---

## 🎯 Objetivo

Reducir el tiempo necesario para revisar manualmente alertas inmobiliarias de distintos portales.

El sistema recibe correos oficiales de alertas, extrae los anuncios, elimina duplicados, filtra por zonas configuradas y genera una única notificación con la información relevante.

El proyecto está diseñado inicialmente para un único cliente y utiliza SQLite como almacenamiento persistente.

---

## ✨ Funcionalidades principales

- Lectura automática de correos mediante IMAP.
- Identificación automática del portal.
- Parser independiente para cada portal.
- Extracción de:
  - enlace
  - identificador externo
  - título
  - precio
  - zona
  - anunciante cuando es posible
- Normalización de URLs.
- Eliminación de parámetros de tracking.
- Deduplicación por URL y por `portal + external_id`.
- Filtrado por zonas.
- Agrupación del correo por portal y zona.
- Envío de resúmenes mediante SMTP.
- Marcado como leídos de los correos procesados correctamente.
- Conservación de correos con error para reintentos.
- Aislamiento de errores entre portales.
- Registro de actividad mediante logs.
- Monitorización de degradación de parsers.
- Retención automática de anuncios.
- Revisión periódica de anuncios publicados por agencias.
- Suite de pruebas automatizadas con Pytest.

---

## 📍 Zonas configuradas

La versión actual está preparada para trabajar con:

- Guindalera
- Fuente del Berro
- Lista
- Goya

Las zonas se cargan desde configuración y pueden modificarse sin cambiar la lógica principal.

---

## 🧱 Arquitectura

```text
┌────────────────────┐
│   Portales          │
│ inmobiliarios       │
└─────────┬──────────┘
          │
          │ Alertas por email
          ▼
┌────────────────────┐
│ Gmail / IMAP       │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ email_connector.py │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ registry.py        │
│ Detecta el portal  │
└─────────┬──────────┘
          ▼
┌─────────────────────────────────────┐
│ Parsers independientes              │
│                                     │
│ Idealista                           │
│ Fotocasa                            │
│ Habitaclia                          │
│ Pisos.com                           │
│ Milanuncios                         │
└─────────┬───────────────────────────┘
          ▼
┌────────────────────┐
│ Normalización      │
│ + extracción       │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Filtro por zona    │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Deduplicación      │
│ SQLite / SQLAlchemy│
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Filtro anunciante  │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Resumen HTML       │
│ SMTP               │
└────────────────────┘
```

---

## 🔄 Flujo de una ejecución

El ciclo principal sigue este orden:

```text
1. Revisar anuncios antiguos publicados por agencias
2. Eliminar anuncios expirados
3. Recuperar nuevos correos inmobiliarios
4. Identificar el portal
5. Extraer anuncios
6. Normalizar datos
7. Filtrar por zona
8. Comprobar duplicados
9. Obtener anunciante cuando sea posible
10. Generar resumen
11. Guardar los anuncios
12. Marcar los correos como leídos
```

El orden de mantenimiento es importante:

```text
review_existing_agencies()
        ↓
clean_history()
        ↓
run_once()
```

De esta forma, un anuncio que llegue a su revisión final puede comprobarse antes de ser eliminado.

---

## 👤 Clasificación del anunciante

Internamente el campo `advertiser` puede contener:

```text
"Particular"
"Nombre de una agencia"
None
```

`None` significa:

```text
No identificado
```

Nunca se interpreta automáticamente un anunciante desconocido como particular.

### Estado por portal

| Portal | Identificación del anunciante |
|---|---|
| Fotocasa | Particular / agencia / no identificado |
| Habitaclia | Particular / agencia / no identificado |
| Pisos.com | Particular / agencia / no identificado |
| Idealista | No identificado hasta disponer de acceso oficial |
| Milanuncios | Particular según el filtro configurado en la alerta |

---

## 🔁 Seguimiento de anuncios de agencias

Una de las reglas de negocio principales del proyecto es detectar si un inmueble inicialmente publicado por una agencia cambia posteriormente de situación.

Para:

- Fotocasa
- Habitaclia
- Pisos.com

los anuncios identificados como agencia se revisan aproximadamente en:

```text
Día 30
Día 45
Día 60
Día 75
Día 90
```

### Posibles resultados

#### Agencia → Agencia

No se vuelve a notificar.

Aunque cambie el nombre de la agencia, el sistema mantiene la clasificación como agencia y continúa con el calendario de revisiones.

#### Agencia → Particular

El sistema:

1. actualiza el anunciante;
2. reinicia el periodo de retención;
3. vuelve a enviar el anuncio;
4. deja de realizar revisiones de agencia.

#### Agencia → No identificado

Se considera también un cambio relevante.

Se actualiza el anuncio, se reinicia la retención y se vuelve a notificar.

#### Error HTTP

Un fallo de red no se interpreta como cambio de anunciante.

La revisión no se consume y podrá reintentarse posteriormente.

---

## ⏱ Política de retención

La retención depende del portal y del estado del anunciante.

### Idealista y Milanuncios

```text
7 días desde detected_at
```

No se realizan revisiones posteriores de anunciante.

### Fotocasa, Habitaclia y Pisos.com

#### Particular o No identificado

```text
30 días desde retention_started_at
```

#### Agencia

Puede permanecer hasta aproximadamente 90 días mientras se realizan las revisiones.

Si sigue siendo agencia en la revisión final, el registro se elimina.

---

## 🗃 Modelo de datos

La entidad principal es:

```python
PropertyListing
```

Campos principales:

| Campo | Descripción |
|---|---|
| `id` | Clave primaria |
| `portal` | Portal de origen |
| `external_id` | Identificador del anuncio |
| `title` | Título normalizado |
| `price` | Precio |
| `zone` | Zona |
| `advertiser` | Particular, agencia o `None` |
| `url` | URL canónica |
| `published_at` | Fecha de publicación si existe |
| `detected_at` | Primera detección |
| `retention_started_at` | Inicio del periodo de retención |
| `advertiser_check_count` | Etapa de revisión del anunciante |
| `last_advertiser_check_at` | Última revisión realizada |
| `raw_data` | Datos originales para diagnóstico |

### Dos relojes diferentes

`detected_at`:

- no cambia;
- controla la edad original del anuncio;
- controla las revisiones de agencia.

`retention_started_at`:

- controla la eliminación;
- se reinicia si una agencia pasa a Particular o No identificado.

---

## 📁 Estructura del proyecto

```text
buscador-inmobiliario/
│
├── data/
│   └── inmuebles.db
│
├── logs/
│   └── bot.log
│
├── src/
│   ├── connectors/
│   │   └── email_connector.py
│   │
│   ├── monitoring/
│   │   └── parser_health.py
│   │
│   ├── notifications/
│   │   └── email_sender.py
│   │
│   ├── parsers/
│   │   ├── idealista_parser.py
│   │   ├── fotocasa_parser.py
│   │   ├── habitaclia_parser.py
│   │   ├── pisos_parser.py
│   │   ├── milanuncios_parser.py
│   │   ├── listing_details.py
│   │   └── registry.py
│   │
│   ├── services/
│   │   └── listing_maintenance.py
│   │
│   ├── config.py
│   ├── database.py
│   ├── logging_config.py
│   ├── main.py
│   ├── models.py
│   ├── pipeline.py
│   └── scheduler.py
│
├── tests/
│
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 🧩 Responsabilidad de cada módulo

### `src/main.py`

Orquestador principal.

Coordina:

- mantenimiento;
- limpieza;
- lectura de Gmail;
- parsing;
- deduplicación;
- envío;
- persistencia;
- marcado de correos.

Funciones principales:

```python
process_email()
run_once()
review_existing_agencies()
clean_history()
run_cycle()
main()
```

---

### `src/config.py`

Centraliza la configuración mediante variables de entorno.

Gestiona, entre otros:

- base de datos;
- zonas;
- IMAP;
- SMTP;
- destinatario;
- frecuencia de ejecución.

Las credenciales reales nunca deben almacenarse directamente en el código.

---

### `src/database.py`

Gestiona SQLAlchemy.

Elementos principales:

```python
engine
SessionLocal
create_database()
```

`create_database()` crea tablas que todavía no existen.

No realiza migraciones automáticas de columnas existentes.

---

### `src/models.py`

Define los modelos persistentes.

Principales modelos:

```python
PropertyListing
ParserHealthAlert
```

---

### `src/pipeline.py`

Contiene reglas de negocio relacionadas con los anuncios.

Funciones principales:

```python
normalize_url()
listing_exists()
save_listing()
is_allowed_zone()
process_listing()
delete_expired_listings()
```

---

### `src/connectors/email_connector.py`

Gestiona la conexión IMAP.

Responsabilidades:

- conectar con Gmail;
- recuperar correos inmobiliarios no leídos;
- mantenerlos sin leer durante el procesamiento;
- marcar como leídos los correos procesados correctamente.

Funciones principales:

```python
connect_to_mailbox()
fetch_unread_emails()
mark_emails_as_read()
```

---

### `src/parsers/registry.py`

Actúa como registro de parsers.

Permite identificar qué parser debe procesar cada email sin concentrar toda la lógica específica de los portales en `main.py`.

---

### `src/parsers/*_parser.py`

Cada portal dispone de un parser independiente.

Responsabilidades habituales:

```python
is_*_email()
extract_*_links()
extract_*_id()
```

Esta separación permite modificar un portal sin afectar al resto.

---

### `src/parsers/listing_details.py`

Contiene lógica de extracción más detallada.

Entre otras tareas:

- normalización de texto;
- extracción de precio;
- asociación de precios con anuncios;
- título;
- zona;
- extracción del anunciante;
- acceso puntual a fichas individuales cuando es técnicamente posible.

---

### `src/services/listing_maintenance.py`

Gestiona las revisiones periódicas de anuncios publicados por agencias.

Funciones principales:

```python
ensure_utc()
is_particular()
is_agency()
get_due_review_stage()
fetch_current_advertiser()
review_agency_listings()
```

También soporta recuperación después de periodos de inactividad.

Ejemplo:

```text
Bot apagado en día 30
Bot apagado en día 45
Bot vuelve en día 62

→ realiza una única revisión
→ salta directamente a la etapa correspondiente al día 60
```

---

### `src/notifications/email_sender.py`

Genera el resumen enviado al cliente.

El contenido se organiza:

```text
Portal
└── Zona
    ├── Inmueble
    ├── Inmueble
    └── Inmueble
```

Los portales tienen estilos visuales diferenciados.

El sistema almacena todos los anuncios, pero el correo operativo prioriza:

- Particulares
- No identificados

Si una ejecución contiene únicamente anuncios de agencias, no es necesario enviar resumen.

---

### `src/monitoring/parser_health.py`

Detecta posibles cambios o roturas en los correos de los portales.

Casos monitorizados:

- correo reconocido con 0 enlaces;
- degradación masiva de `external_id`;
- degradación en la extracción de precio.

Configuración actual:

```text
Cooldown de alertas: 12 horas
Muestra mínima parcial: 3 anuncios
Umbral de fallo: 80 %
```

Esto permite detectar cambios en el formato de los portales antes de que el problema pase desapercibido.

---

### `src/scheduler.py`

Gestiona la ejecución periódica mediante APScheduler.

El scheduler debe ejecutar:

```python
run_cycle
```

y no solamente:

```python
run_once
```

porque cada ciclo debe incluir también:

```text
revisión de agencias
+
limpieza
+
nuevos emails
```

---

## 📧 Gestión de errores

El sistema sigue una estrategia orientada a no perder anuncios.

### Procesamiento correcto

```text
Correo procesado
→ anuncios enviados/guardados
→ correo marcado como leído
```

### Error

```text
Correo
→ error de parser / SMTP / procesamiento
→ permanece sin leer
→ podrá reintentarse
```

Además, un error de un portal no debe impedir procesar los demás.

---

## 🩺 Parser Health Check

Un correo reconocido como alerta que devuelve:

```text
0 enlaces
```

se considera una posible rotura del parser.

El sistema puede:

- guardar la incidencia;
- enviar una alerta técnica;
- mantener el correo sin leer;
- aplicar cooldown para no generar spam técnico.

También existe detección de degradación parcial.

---

## 🧪 Testing

El proyecto dispone actualmente de:

```text
74 tests automatizados
```

ejecutados con:

```bash
python -m pytest -v
```

Cobertura relevante:

- guardado en SQLite;
- normalización de URL;
- deduplicación;
- filtros de zona;
- conectores de correo;
- errores SMTP;
- errores de parsers;
- Milanuncios;
- parser health;
- retención;
- revisiones de agencia;
- fallos HTTP;
- rollback de notificaciones;
- recuperación tras downtime.

Las pruebas utilizan bases SQLite temporales y nunca deben modificar:

```text
data/inmuebles.db
```

---

## 🛠 Stack tecnológico

- Python 3
- SQLAlchemy
- SQLite
- BeautifulSoup
- requests
- imap-tools
- SMTP / STARTTLS
- APScheduler
- Pytest

---

## ⚙️ Configuración

Crear un archivo `.env` a partir de:

```text
.env.example
```

Ejemplo conceptual:

```env
DATABASE_URL=sqlite:///data/inmuebles.db

IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=
IMAP_PASSWORD=

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

NOTIFICATION_EMAIL=

ZONES=Guindalera,Fuente del Berro,Lista,Goya

CHECK_INTERVAL_MINUTES=5
```

> No introducir credenciales reales en `.env.example`.

---

## ▶️ Ejecución local

Crear y activar el entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Ejecutar:

```powershell
python -m src.main
```

---

## ✅ Ejecutar pruebas

Todas:

```powershell
python -m pytest -v
```

Mantenimiento de anunciantes:

```powershell
python -m pytest tests/test_listing_maintenance.py -v
```

Base de datos:

```powershell
python -m pytest tests/test_database.py -v
```

Parser health:

```powershell
python -m pytest tests/test_parser_health.py -v
```

---

## 🔐 Seguridad

Nunca subir al repositorio:

```text
.env
data/inmuebles.db
logs/
.venv/
correos .eml reales
credenciales
tokens
API keys
contraseñas de aplicación
```

Las credenciales deben existir únicamente en:

```text
.env
```

durante desarrollo, o en el sistema de secretos / variables de entorno del proveedor cloud en producción.

---

## ⚠️ Limitaciones actuales

### Idealista

El correo permite obtener:

- URL
- ID
- título
- precio
- zona

La identificación del anunciante está pendiente de acceso a una vía oficial.

No se utiliza scraping directo para intentar evitar las protecciones del portal.

### Milanuncios

La clasificación como Particular depende de que las alertas estén configuradas en Milanuncios con:

```text
Tipo de vendedor = Particular
```

La ubicación del correo puede no contener siempre uno de los cuatro barrios objetivo.

Cuando no puede identificarse un barrio concreto se utiliza:

```text
Madrid Capital
```

como fallback.

### Correos administrativos

El filtro IMAP actual selecciona mensajes enviados por los portales, por lo que determinados correos administrativos (bienvenida, activación de cuenta, etc.) también pueden llegar hasta la capa de parsing.

Una mejora futura es endurecer la detección de alertas reales por asunto/formato para reducir falsos positivos en los health checks.

---

## 🚧 Estado del proyecto

### Completado

- [x] Integración de los cinco portales.
- [x] Extracción de anuncios reales.
- [x] IMAP.
- [x] SMTP.
- [x] SQLite.
- [x] Deduplicación.
- [x] Filtro de zonas.
- [x] Anunciante en Fotocasa.
- [x] Anunciante en Habitaclia.
- [x] Anunciante en Pisos.com.
- [x] Clasificación de Milanuncios mediante alerta de Particular.
- [x] Parser health.
- [x] Logs.
- [x] Retención diferenciada.
- [x] Seguimiento de agencias a 30 / 45 / 60 / 75 / 90 días.
- [x] Gestión de downtime.
- [x] 74 pruebas automatizadas.

### Pendiente para cerrar la V1

- [ ] Validar definitivamente el filtro geográfico de Milanuncios.
- [ ] Endurecer la detección de correos de alerta frente a emails administrativos.
- [ ] Validar una ejecución real completa después del último cambio de esquema de SQLite.
- [ ] Conectar y validar `scheduler.py` con `run_cycle()`.
- [ ] Ejecutar automáticamente cada cinco minutos.
- [ ] Desplegar en cloud.
- [ ] Configurar almacenamiento persistente para SQLite.
- [ ] Configurar logs persistentes en producción.
- [ ] Configurar secretos / variables de entorno en cloud.
- [ ] Configurar reinicio automático del proceso.
- [ ] Validar IMAP desde cloud.
- [ ] Validar SMTP desde cloud.
- [ ] Validar persistencia después de reinicios.
- [ ] Validar health checks en ejecución real de producción.
- [ ] Integrar identificación oficial de anunciante de Idealista cuando exista acceso.

---

## 🗺 Roadmap

### V1

Objetivo:

```text
Servicio completamente automático y estable para un cliente.
```

Incluye:

- cinco portales;
- filtros;
- deduplicación;
- anunciantes;
- retención;
- mantenimiento;
- correo;
- pruebas;
- cloud.

### V2

Posibles mejoras:

- panel web;
- gestión de clientes;
- gestión de zonas;
- configuración de portales;
- destinatarios configurables;
- histórico;
- filtros por precio;
- estados de ejecución;
- métricas;
- gestión de errores;
- multiusuario;
- PostgreSQL.

---

## 📈 Posible evolución del producto

La arquitectura actual permite evolucionar hacia un servicio SaaS con:

```text
Cliente
├── zonas
├── portales
├── destinatarios
├── frecuencia
├── filtros
└── historial
```

En ese escenario sería recomendable migrar:

```text
SQLite → PostgreSQL
```

y añadir una API backend y un panel de administración.

---

## 📌 Estado actual

La lógica principal está desarrollada y respaldada por 74 pruebas automatizadas.

La siguiente fase del proyecto es principalmente operativa:

```text
automatización
+
cloud
+
persistencia
+
validación de producción
```

---

## Autor

Proyecto personal de software enfocado en:

- automatización;
- backend;
- integración de sistemas;
- procesamiento de datos;
- reglas de negocio;
- tolerancia a fallos;
- testing.

