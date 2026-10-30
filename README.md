# Rates Reporter — Tasas diarias BCV y Binance P2P

Script diario en Python que consulta tasas de cambio en Venezuela (BCV USD, BCV EUR, Binance P2P USDT/VES), aplica reglas de ajuste configurables y genera un mensaje listo para enviar por WhatsApp (via CallMeBot) o guardar localmente.

## Requisitos

- Python 3.11+
- pip

## Instalacion

```bash
cd rates-reporter
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
pip install -r requirements.txt
```

Copiar y editar los archivos de configuracion:

```bash
cp config.example.yaml config.yaml
cp .env.example .env
```

Editar `config.yaml` con los ajustes deseados por tasa.

Editar `.env` con `CALLMEBOT_APIKEY` y `config.yaml` con el numero de telefono si se desea enviar por WhatsApp.

## Uso

### Ejecucion manual

```bash
python rate_reporter.py --config config.yaml
```

El mensaje se imprime en consola y se guarda en `latest-rates-message.txt`.

### Ejecucion automatica con cron

Agregar al crontab diario a las 9:00 AM hora Venezuela:

```cron
CRON_TZ=America/Caracas
0 9 * * * cd /ruta/rates-reporter && /ruta/rates-reporter/.venv/bin/python rate_reporter.py --config /ruta/rates-reporter/config.yaml >> /ruta/rates-reporter/logs/cron.log 2>&1
```

Ajustar `/ruta/rates-reporter` a la ubicacion real del proyecto.

## Como cambiar las reglas de ajuste

Editar `config.yaml` en la seccion `rates` de cada tasa:

### Restar 0.2% (sin monto fijo)

```yaml
bcv_usd:
  adjustments:
    percent_subtract: 0.2
    fixed_subtract_bs: 0.0
```

### Restar 10 Bs (sin porcentaje)

```yaml
bcv_usd:
  adjustments:
    percent_subtract: 0.0
    fixed_subtract_bs: 10.0
```

### Aplicar ambos ajustes (primero %, luego fijo)

```yaml
bcv_usd:
  adjustments:
    percent_subtract: 0.2
    fixed_subtract_bs: 10.0
```

Orden: `ajustada = (base * (1 - %/100)) - fijo`

### Desactivar ajustes para una tasa

```yaml
bcv_usd:
  adjustments:
    percent_subtract: 0.0
    fixed_subtract_bs: 0.0
```

### Desactivar una tasa completamente

```yaml
bcv_eur:
  enabled: false
```

## WhatsApp con CallMeBot

Para recibir el mensaje diario en WhatsApp sin usar la API de Meta:

1. Anda a [callmebot.com](https://www.callmebot.com) y obten tu API key.
2. Agrega el numero de CallMeBot a tus contactos de WhatsApp y activalo.
3. Agrega tu numero de telefono en `config.yaml`:
   ```yaml
   callmebot:
     enabled: true
     phone: "584141234567"
     apikey_env: "CALLMEBOT_APIKEY"
   ```
4. Agrega tu API key en `.env`:
   ```env
   CALLMEBOT_APIKEY=tu_api_key
   ```

Si `enabled: false`, el script solo imprime y guarda el mensaje localmente.

## Variables de entorno

| Variable | Descripcion |
|---|---|
| `CALLMEBOT_APIKEY` | API key de callmebot.com para enviar mensajes por WhatsApp |

## Configuracion YAML

Ver `config.example.yaml` como referencia completa. Secciones principales:

- `timezone` — zona horaria para el mensaje
- `round_decimals` — decimales para redondeo final
- `output` — impresion en consola y guardado en archivo
- `callmebot` — envio por WhatsApp via CallMeBot
- `rates.*.adjustments` — descuentos por tasa
- `rates.*.binance` — parametros del cliente P2P (asset, trade_type, aggregation, etc.)

## Pruebas

```bash
pytest tests/ -v
```

## Advertencias

- Binance P2P puede fallar por rate‑limiting, cambios en la API o bloqueos regionales. El script maneja la falla sin detener el reporte de BCV.
- Configurar `fallback_manual_rate` en `binance_usdt` para tener una tasa de respaldo si Binance no responde.
- Usar `trade_type: SELL` para referencia de compra de USDT con VES. Cambiar a `BUY` si se necesita la referencia inversa.
- La API de DolarAPI es publica pero esta sujeta a disponibilidad del proveedor externo.

## Sincronizacion con Odoo (`odoo_sync.py`)

Servicio aparte del reporter de WhatsApp: consulta las 4 tasas y las carga en Odoo.

| Tasa | Fuente | Destino en Odoo |
|---|---|---|
| BCV USD | bcv.org.ve (respaldo: DolarAPI) | tasa contable de VEF (o de USD en empresas en bolivares) + tabla "Tasas de cambio" |
| BCV EUR | bcv.org.ve (respaldo: DolarAPI) | tasa contable de EUR + tabla "Tasas de cambio" |
| Binance compra | Binance P2P USDT/VES BUY, mediana de 10 anuncios | tabla "Tasas de cambio" |
| Binance venta | Binance P2P USDT/VES SELL, mediana de 10 anuncios | tabla "Tasas de cambio" |

- Las tasas contables llevan la **fecha valor** del BCV y se escriben en todas las empresas, sobrescribiendo la del mismo dia.
- La tabla es el modelo `x_tasa_cambio` (Contabilidad > Configuracion > Contabilidad > Tasas de cambio): una fila por ejecucion.
- bcv.org.ve no envia su certificado intermedio correcto; se verifica con `certs/sectigo-public-server-authentication-ca-dv-r36.pem` + raices de certifi.

Variables: `ODOO_BASE_URL`, `ODOO_DATABASE`, `ODOO_API_KEY`, `ODOO_SYNC_TIMES` (por defecto `09:00,17:00`), `TIMEZONE`, `RUN_ON_STARTUP`.

```bash
python odoo_sync.py --dry-run   # consulta y muestra lo que escribiria
python odoo_sync.py             # escribe en Odoo
```

En Coolify corre como app `odoo-rates-sync` con `Dockerfile.odoo` (scheduler `odoo_scheduler.py`, todos los dias a las horas de `ODOO_SYNC_TIMES`).

### Carga historica (`odoo_backfill.py`)

```bash
python odoo_backfill.py 2026-10-01 2026-10-29 [--dry-run]
```

Toma el historico oficial BCV (USD y EUR) de DolarAPI y lo escribe igual que `odoo_sync.py`, una fila por fecha valor
en `x_tasa_cambio` (sin Binance: el P2P no tiene historico). No duplica filas de fechas ya cargadas.
