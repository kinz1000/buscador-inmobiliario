## Portales

- [x] Fotocasa
- [x] Idealista
- [x] Habitaclia
- [x] Pisos.com
- [x] Milanuncios

## Zonas

- Guindalera
- Fuente del Berro
- Lista
- Goya

## Desarrollo completado

- [x] Lectura de correos mediante IMAP.
- [x] Envío de resúmenes mediante SMTP.
- [x] Credenciales IMAP y SMTP separadas.
- [x] Filtrado de correos por portal inmobiliario.
- [x] Marcado de correos procesados como leídos.
- [x] Conservación de correos cuando ocurre un error.
- [x] Aislamiento de errores por correo.
- [x] Detección de anuncios duplicados.
- [x] Almacenamiento de anuncios en SQLite.
- [x] Eliminación de anuncios con más de 30 días.
- [x] Agrupación del correo por portal y zona.
- [x] Extracción real de Fotocasa.
- [x] Extracción real de Habitaclia.
- [x] Extracción real de Pisos.com.
- [x] Extracción real de Idealista desde el correo.
- [x] Detección y resolución de enlaces de Milanuncios.
- [x] Extracción de precio por tarjeta en Milanuncios.
- [x] Asociación de cada tarjeta de Milanuncios con su URL real.
- [x] Clasificación de Milanuncios como Particular mediante alertas filtradas.
- [x] Uso de "Madrid Capital" como zona fallback en Milanuncios cuando no se identifica un barrio concreto.
- [x] Normalización de URL.
- [x] Eliminación de parámetros de seguimiento.
- [x] Unificación de HTTP/HTTPS, www y barras finales.
- [x] Configuración de pruebas automáticas con pytest.
- [x] Clasificación de Fotocasa entre agencia, particular y no identificado.
- [x] Colores diferenciados por portal en el resumen.
- [x] Crear un Gmail exclusivo para producción.
- [x] Configurar filtros de Gmail para los cinco portales.
- [x] Configurar los filtros de Gmail con "Nunca enviarlo a Spam".
- [x] Añadir filtros por dominio/remitente para Fotocasa, Idealista, Habitaclia, Pisos.com y Milanuncios.
- [x] Confirmar que la carpeta Spam está visible mediante IMAP.

## Desarrollo pendiente

- [x] Recibir un correo real de Idealista.
- [x] Recibir un correo real de Habitaclia.
- [x] Recibir un correo real de Pisos.com.
- [x] Recibir un correo real de Milanuncios.
- [x] Adaptar Fotocasa al formato de sus correos reales.
- [x] Adaptar Habitaclia al formato de sus correos reales.
- [x] Adaptar Pisos.com al formato de sus correos reales.
- [x] Adaptar Idealista al formato de sus correos reales.
- [x] Adaptar Milanuncios para asociar cada tarjeta con su precio y URL.
- [ ] Aplicar el filtro definitivo de zonas a Milanuncios.
- [ ] Completar información del vendedor o particular en todos los portales.
- [ ] Integrar API oficial de Idealista para vendedor/particular cuando haya acceso.
- [ ] Crear las pruebas de base de datos.
- [ ] Preparar el proyecto para ejecutarlo en cloud.
- [ ] Migrar todas las alertas de los portales al Gmail de producción.
- [ ] Validar la recepción IMAP con el Gmail de producción.
- [ ] Validar el envío SMTP con la configuración definitiva de producción.
- [ ] Crear un sistema de detección de cambios en los formatos de los portales.

## Pruebas completadas

### Conector de correo

- [x] El filtro contiene los cinco portales.
- [x] La recuperación utiliza el filtro inmobiliario.
- [x] Los mensajes se recuperan sin marcarlos automáticamente como leídos.
- [x] Los UID repetidos se eliminan antes de marcar los correos.
- [x] Una lista vacía de UID no abre una conexión innecesaria.

### Procesamiento principal

- [x] Un anuncio existente se reconoce como duplicado.
- [x] Un error del parser queda controlado.
- [x] Un anuncio nuevo de Fotocasa se procesa correctamente.
- [x] Un correo con duplicados se marca como leído.
- [x] El bot continúa después de encontrar un correo defectuoso.
- [x] Un fallo SMTP mantiene el correo sin leer.
- [x] Un fallo SMTP evita guardar parcialmente los anuncios.
- [x] Milanuncios extrae precios distintos por tarjeta.
- [x] Milanuncios asocia cada tarjeta con su URL real.
- [x] Milanuncios clasifica los anuncios como Particular.
- [x] Milanuncios usa Madrid Capital como fallback cuando no identifica una zona concreta.

### Normalización de URL

- [x] Se eliminan parámetros de seguimiento.
- [x] Se eliminan fragmentos como #contacto.
- [x] Se unifican HTTP y HTTPS.
- [x] Se unifican direcciones con y sin www.
- [x] Se eliminan barras finales.
- [x] Dos versiones de la misma URL se consideran iguales.
- [x] Dos anuncios diferentes continúan siendo diferentes.

### Configuración Gmail de producción

- [x] Gmail exclusivo de producción creado.
- [x] Filtros creados para los cinco portales.
- [x] Configurado "Nunca enviarlo a Spam".
- [x] Filtros basados en dominios/remitentes de los portales.
- [x] Carpeta Spam visible por IMAP.

### Resultado actual

14 pruebas automáticas superadas

## Pruebas pendientes

### Base de datos temporal

- [ ] Crear una SQLite temporal exclusiva para las pruebas.
- [ ] Comprobar que se puede guardar un anuncio nuevo.
- [ ] Comprobar que un mismo anuncio no puede guardarse dos veces.
- [ ] Comprobar duplicados mediante URL normalizada.
- [ ] Comprobar duplicados mediante portal e identificador externo.
- [ ] Comprobar que se eliminan registros con más de 30 días.
- [ ] Comprobar que no se eliminan registros recientes.
- [ ] Comprobar las zonas permitidas.
- [ ] Confirmar que las pruebas no modifican data/inmuebles.db.

### Pruebas pendientes con correos reales

- [x] Probar un correo real con un anuncio de Idealista.
- [ ] Probar un correo real con varios anuncios de Idealista.
- [x] Probar un correo real de Habitaclia.
- [x] Probar un correo real de Pisos.com.
- [x] Probar un correo real de Milanuncios.
- [x] Probar la extracción de precio por anuncio en Fotocasa.
- [x] Probar la extracción de título por anuncio en Fotocasa.
- [x] Probar la extracción de zona por anuncio en Fotocasa/Habitaclia/Pisos.com.
- [x] Probar la extracción de precio por tarjeta en Milanuncios.
- [x] Probar la asociación tarjeta/URL en Milanuncios.
- [ ] Probar el filtro definitivo de las cuatro zonas en Milanuncios.

### Pruebas pendientes en producción

- [ ] Confirmar que llegan alertas reales al Gmail de producción.
- [ ] Confirmar que los filtros evitan que las alertas entren en Spam.
- [ ] Confirmar que IMAP recupera correctamente los correos de producción.
- [ ] Confirmar que SMTP envía correctamente desde la configuración definitiva.
- [ ] Ejecutar el bot manualmente con el Gmail de producción.
- [ ] Confirmar que los correos procesados se marcan como leídos en producción.

### Pruebas pendientes en cloud

- [ ] Comprobar la ejecución programada cada cinco minutos.
- [ ] Comprobar la persistencia de SQLite después de reiniciar.
- [ ] Comprobar el acceso mediante variables de entorno.
- [ ] Comprobar el envío de correos desde cloud.
- [ ] Comprobar la generación y conservación de logs.

## Decisiones tomadas

- El bot se ejecutará finalmente en la nube.
- SQLite se utilizará inicialmente para un único cliente.
- Los anuncios se conservarán durante 30 días.
- Los correos procesados correctamente se marcarán como leídos.
- Los correos con errores permanecerán sin leer.
- Un error de un portal no detendrá los demás.
- Los anuncios sin anunciante identificado se conservarán como "No identificado".
- No se asumirá que un anunciante desconocido es particular.
- Milanuncios utilizará alertas configuradas con "Tipo de vendedor = Particular".
- Milanuncios utilizará "Madrid Capital" como fallback cuando no pueda identificar Guindalera, Fuente del Berro, Lista o Goya.
- Idealista utilizará la API oficial para identificar anunciante cuando se obtenga acceso.
- Se utilizará un Gmail exclusivo cuando el proyecto pase a producción.
- Los cinco portales tendrán filtros de Gmail configurados para evitar Spam.
- Las credenciales del Gmail de producción se almacenarán únicamente mediante variables de entorno.
- Durante el desarrollo se continuará utilizando el correo actual hasta completar la migración.
- No se implementará lógica específica de un portal sin disponer antes de un correo real.

## Comandos útiles

### Activar el entorno virtual

```powershell
.\.venv\Scripts\Activate.ps1

### Ejecutar el bot

powershell
python -m src.main


### Ejecutar las pruebas

powershell
python -m pytest -v


### Comprobar la configuración SMTP

powershell
python -c "from src.config import settings; print('SMTP:', settings.smtp_user, '| Contraseña configurada:', bool(settings.smtp_password))"


## Próximo paso

Crear pruebas de integración para SQLite utilizando una base de datos temporal, sin modificar data/inmuebles.db.

## Seguridad

Nunca guardar contraseñas, claves de aplicación ni credenciales dentro de este documento. Todas las credenciales deben permanecer exclusivamente en el archivo .env.