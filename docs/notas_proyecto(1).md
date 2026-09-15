# Notas del buscador inmobiliario

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
- [x] Crear pruebas de base de datos con SQLite temporal.
- [x] Confirmar que los tests de base de datos no modifican `data/inmuebles.db`.
- [x] Crear sistema de health check para detectar posibles cambios en los parsers.
- [x] Detectar correos reconocidos que devuelven 0 enlaces.
- [x] Mantener sin leer los correos cuando un parser reconocido devuelve 0 enlaces.
- [x] Enviar alerta técnica por correo cuando un parser devuelve 0 enlaces.
- [x] Crear cooldown de 12 horas por portal e incidencia para evitar alertas repetitivas.
- [x] Persistir incidencias de parsers en SQLite mediante `parser_health_alerts`.
- [x] Detectar degradación parcial en `external_id`.
- [x] Detectar degradación parcial en extracción de precios.
- [x] Configurar un mínimo de 3 anuncios para alertas de degradación parcial.
- [x] Configurar un umbral del 80 % de fallos para lanzar alertas de degradación parcial.
- [x] Separar alertas por portal e `issue_code`.
- [x] Probar automáticamente el cooldown de alertas.
- [x] Probar automáticamente la independencia de alertas entre portales.
- [x] Configurar limpieza periódica de correos antiguos de alertas en Gmail mediante Google Apps Script.
- [x] Configurar eliminación de alertas de Gmail con más de seis meses.

## Desarrollo pendiente

- [ ] Aplicar/validar el filtro definitivo de zonas a Milanuncios.
- [ ] Completar información del vendedor o particular en todos los portales.
- [ ] Integrar API oficial de Idealista para vendedor/particular cuando haya acceso.
- [ ] Preparar el proyecto para ejecutarlo en cloud.
- [ ] Migrar todas las alertas de los portales al Gmail de producción.
- [ ] Validar la recepción IMAP con el Gmail de producción.
- [ ] Validar el envío SMTP con la configuración definitiva de producción.
- [ ] Preparar persistencia de SQLite en cloud.
- [ ] Preparar logs persistentes para producción.
- [ ] Preparar reinicio automático del proceso en cloud.
- [ ] Validar ejecución programada cada cinco minutos en producción.

## Estado de APIs y dependencias externas

### Idealista

- [x] Parser de correos reales funcionando.
- [x] Extracción de enlace, ID, título, precio y zona desde el correo.
- [ ] Identificación de anunciante pendiente.
- [x] API oficial solicitada.
- [ ] Esperando acceso/key de la API oficial de Idealista.

Hasta disponer de la API oficial, el anunciante de Idealista permanece como:

```python
listing_advertiser = None
```

y se muestra como `No identificado`.

No se utilizará scraping directo de Idealista para sustituir la API oficial. La integración del anunciante queda pendiente hasta recibir acceso a la API.

### Milanuncios

Milanuncios no proporciona actualmente en el correo el tipo de vendedor de cada anuncio de forma explícita.

La clasificación como `Particular` depende de que las alertas creadas en la propia web de Milanuncios estén configuradas con:

```text
Tipo de vendedor = Particular
```

Por tanto:

- El bot no deduce mediante scraping que el anuncio sea particular.
- El bot confía en el filtro configurado previamente en la web de Milanuncios.
- Las búsquedas/alertas de Milanuncios deben mantenerse configuradas como `Particular`.
- Si se modifica ese filtro en Milanuncios, la clasificación automática dejaría de ser fiable.
- La precisión geográfica también depende parcialmente de los filtros disponibles en Milanuncios.
- Las alertas deben configurarse lo más cerca posible de Guindalera, Fuente del Berro, Lista y Goya.
- Cuando el correo no permite identificar una de las cuatro zonas objetivo, se utiliza `Madrid Capital` como fallback.

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
- [x] Un correo reconocido con 0 enlaces se considera posible fallo de parser.
- [x] Un correo reconocido con 0 enlaces permanece sin leer.
- [x] La alerta del parser se envía cuando corresponde.
- [x] Milanuncios extrae precios distintos por tarjeta.
- [x] Milanuncios asocia cada tarjeta con su URL real.
- [x] Milanuncios clasifica los anuncios como Particular.
- [x] Milanuncios usa Madrid Capital como fallback cuando no identifica una zona concreta.

### Parser de Milanuncios

- [x] Probar un correo `.eml` real de Milanuncios.
- [x] Detectar correctamente el correo como Milanuncios.
- [x] Extraer `external_id` desde la URL real.
- [x] Detectar las tarjetas individuales del correo.
- [x] Extraer los precios individuales de las tarjetas.
- [x] Extraer `Madrid Capital` como ubicación.
- [x] Confirmar que cada tarjeta tiene `external_id`.
- [x] Confirmar que cada tarjeta devuelve una URL única.
- [x] Evitar que los tests dependan de respuestas externas de Milanuncios.

### Base de datos temporal

- [x] Crear una SQLite temporal exclusiva para las pruebas.
- [x] Comprobar que se puede guardar un anuncio nuevo.
- [x] Comprobar que un mismo anuncio no puede guardarse dos veces.
- [x] Comprobar duplicados mediante URL normalizada.
- [x] Comprobar duplicados mediante portal e identificador externo.
- [x] Comprobar que el mismo `external_id` en portales distintos no se considera duplicado.
- [x] Comprobar que se eliminan registros con más de 30 días.
- [x] Comprobar que no se eliminan registros recientes.
- [x] Comprobar las zonas permitidas.
- [x] Comprobar las zonas no permitidas.
- [x] Confirmar que las pruebas no modifican `data/inmuebles.db`.

### Health check de parsers

- [x] Crear tabla `parser_health_alerts`.
- [x] Registrar portal e `issue_code`.
- [x] Registrar primera y última detección.
- [x] Registrar último envío de alerta.
- [x] Primera incidencia genera una alerta.
- [x] Una incidencia repetida durante el cooldown no genera otra alerta.
- [x] Una incidencia vuelve a alertar después de 12 horas.
- [x] El mismo problema en distintos portales se controla de forma independiente.
- [x] No alertar por degradación parcial si hay menos de 3 anuncios.
- [x] Alertar cuando el 80 % o más de los anuncios falla.
- [x] No alertar si el porcentaje de fallo está por debajo del 80 %.
- [x] Detectar fallo masivo de `external_id`.
- [x] Detectar fallo masivo de precio.

### Normalización de URL

- [x] Se eliminan parámetros de seguimiento.
- [x] Se eliminan fragmentos como `#contacto`.
- [x] Se unifican HTTP y HTTPS.
- [x] Se unifican direcciones con y sin www.
- [x] Se eliminan barras finales.
- [x] Dos versiones de la misma URL se consideran iguales.
- [x] Dos anuncios diferentes continúan siendo diferentes.

### Configuración Gmail de producción

- [x] Gmail exclusivo de producción creado.
- [x] Filtros creados para los cinco portales.
- [x] Configurado `Nunca enviarlo a Spam`.
- [x] Filtros basados en dominios/remitentes de los portales.
- [x] Carpeta Spam visible por IMAP.
- [x] Limpieza periódica de alertas antiguas configurada.
- [x] Trigger periódico de Google Apps Script configurado.

### Resultado actual

**50 pruebas automáticas superadas.**

## Pruebas pendientes

### Correos reales

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

### Producción

- [ ] Confirmar que llegan alertas reales al Gmail de producción.
- [ ] Confirmar que los filtros evitan que las alertas entren en Spam.
- [ ] Confirmar que IMAP recupera correctamente los correos de producción.
- [ ] Confirmar que SMTP envía correctamente desde la configuración definitiva.
- [ ] Ejecutar el bot manualmente con el Gmail de producción.
- [ ] Confirmar que los correos procesados se marcan como leídos en producción.
- [ ] Confirmar que los correos con errores permanecen sin leer en producción.
- [ ] Confirmar que las alertas de health check llegan correctamente.
- [ ] Confirmar que el cooldown evita múltiples avisos del mismo error.

### Cloud

- [ ] Comprobar la ejecución programada cada cinco minutos.
- [ ] Comprobar la persistencia de SQLite después de reiniciar.
- [ ] Comprobar el acceso mediante variables de entorno.
- [ ] Comprobar el envío de correos desde cloud.
- [ ] Comprobar la recepción IMAP desde cloud.
- [ ] Comprobar la generación y conservación de logs.
- [ ] Comprobar el reinicio automático si el proceso falla.
- [ ] Comprobar que `parser_health_alerts` persiste después de reiniciar.
- [ ] Confirmar que los cooldown de alertas siguen funcionando después de reinicios.

## Decisiones tomadas

- El bot se ejecutará finalmente en la nube.
- SQLite se utilizará inicialmente para un único cliente.
- Los anuncios se conservarán durante 30 días.
- Los correos procesados correctamente se marcarán como leídos.
- Los correos con errores permanecerán sin leer.
- Un correo reconocido como perteneciente a un portal pero con 0 enlaces se considerará posible fallo de parser y permanecerá sin leer.
- Un error de un portal no detendrá los demás.
- Los anuncios sin anunciante identificado se conservarán como `No identificado`.
- No se asumirá que un anunciante desconocido es particular.
- Milanuncios utilizará alertas configuradas con `Tipo de vendedor = Particular`.
- La identificación de particulares en Milanuncios depende del filtro aplicado en la propia web de Milanuncios.
- La precisión de las zonas de Milanuncios depende parcialmente de los filtros disponibles en la propia plataforma.
- Milanuncios utilizará `Madrid Capital` como fallback cuando no pueda identificar Guindalera, Fuente del Berro, Lista o Goya.
- Idealista utilizará la API oficial para identificar anunciante cuando se obtenga acceso.
- Actualmente se está esperando la key/acceso de la API oficial de Idealista.
- Hasta disponer de la API, el anunciante de Idealista permanecerá como `No identificado`.
- No se utilizará scraping directo de Idealista para sustituir la API oficial.
- Se utilizará un Gmail exclusivo para producción.
- Los cinco portales tendrán filtros de Gmail para evitar Spam.
- Las credenciales de producción se almacenarán únicamente mediante variables de entorno.
- No se implementará lógica específica de un portal sin disponer antes de un correo real.
- Los health checks de degradación parcial requieren al menos 3 anuncios.
- Los health checks de degradación parcial alertarán cuando falle el 80 % o más.
- Las alertas técnicas tendrán un cooldown de 12 horas por portal y tipo de incidencia.
- Los tests automáticos nunca deben utilizar la base `data/inmuebles.db` real.

## Comandos útiles

### Activar el entorno virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

### Ejecutar el bot

```powershell
python -m src.main
```

### Ejecutar todas las pruebas

```powershell
python -m pytest -v
```

### Ejecutar pruebas de base de datos

```powershell
python -m pytest tests/test_database.py -v
```

### Ejecutar pruebas de health check

```powershell
python -m pytest tests/test_parser_health.py -v
```

### Ejecutar pruebas del procesamiento principal

```powershell
python -m pytest tests/test_main.py -v
```

### Ejecutar pruebas de Milanuncios

```powershell
python -m pytest tests/test_milanuncios_parser.py -v
```

### Comprobar la configuración SMTP

```powershell
python -c "from src.config import settings; print('SMTP:', settings.smtp_user, '| Contraseña configurada:', bool(settings.smtp_password))"
```

### Comprobar las tablas SQLite

```powershell
python -c "import sqlite3; c=sqlite3.connect(r'data/inmuebles.db'); print(c.execute('SELECT name FROM sqlite_master WHERE type=? ORDER BY name', ('table',)).fetchall()); c.close()"
```

## Próximo paso

Preparar el proyecto para producción/cloud mientras se espera el acceso a la API oficial de Idealista.

Orden previsto:

1. Migrar definitivamente las alertas al Gmail de producción.
2. Validar IMAP y SMTP con las credenciales definitivas.
3. Ejecutar manualmente el bot varias veces con correos reales de producción.
4. Confirmar el comportamiento de lectura/no lectura de correos.
5. Preparar almacenamiento persistente para SQLite.
6. Preparar variables de entorno en cloud.
7. Preparar logs y reinicio automático.
8. Programar la ejecución cada cinco minutos.
9. Integrar la API oficial de Idealista cuando se reciba la key.

## Seguridad

Nunca guardar contraseñas, claves de aplicación, API keys ni credenciales dentro de este documento.

Todas las credenciales deben permanecer exclusivamente en:

- `.env` durante desarrollo.
- Variables de entorno o sistema de secretos del proveedor cloud en producción.

El archivo `.env` nunca debe subirse al repositorio.
