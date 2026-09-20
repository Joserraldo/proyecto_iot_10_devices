#!/usr/bin/env python3
"""
provision_devices.py — Registra los 10 dispositivos en Azure IoT Central via DPS
y obtiene los connection strings para poner en .env

Requiere:
  DPS_ID_SCOPE   — ID Scope de la aplicación IoT Central
                   (Administration → Device connection → ID scope)
  DPS_MASTER_KEY — Primary key maestra
                   (Administration → Device connection → Primary key)

Uso:
  python provision_devices.py                       # lee DPS_ID_SCOPE y DPS_MASTER_KEY del entorno
  python provision_devices.py --id-scope 0neXXX --master-key BASE64==

El script:
  1. Deriva la clave simétrica de cada dispositivo desde la clave maestra.
  2. Registra cada dispositivo en DPS (global.azure-devices-provisioning.net).
  3. Imprime la connection string lista para copiar a .env.

NOTA: Ejecutar una vez por dispositivo, o todos juntos.
      Los connection strings obtenidos NO tienen expiración mientras el
      dispositivo exista en IoT Central.
"""

import os
import sys
import time
import hmac
import base64
import hashlib
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PROVISION] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DPS_HOST = "global.azure-devices-provisioning.net"

DEVICES = [
    {"id": "campus-ems-01", "label": "D1  — Estación meteo campus"},
    {"id": "campus-ems-02", "label": "D2  — Meteo patio (bridge Wokwi)"},
    {"id": "campus-ems-03", "label": "D3  — Incendio Bloque A"},
    {"id": "campus-ems-04", "label": "D4  — Incendio Laboratorio"},
    {"id": "campus-ems-05", "label": "D5  — Calidad aire aula"},
    {"id": "campus-ems-06", "label": "D6  — Calidad aire exterior"},
    {"id": "campus-ems-07", "label": "D7  — Acceso principal"},
    {"id": "campus-ems-08", "label": "D8  — Cerramiento norte"},
    {"id": "campus-ems-09", "label": "D9  — Evacuación pasillo"},
    {"id": "campus-ems-10", "label": "D10 — Puesto de mando"},
]


def derive_device_key(master_key: str, device_id: str) -> str:
    """
    Deriva la clave simétrica de un dispositivo usando HMAC-SHA256.
    Este es el método estándar de IoT Central para enrollment de grupo.
    """
    master_bytes = base64.b64decode(master_key)
    device_bytes = hmac.new(master_bytes, device_id.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(device_bytes).decode("utf-8")


def provision_device(id_scope: str, device_id: str, device_key: str) -> str | None:
    """
    Registra el dispositivo en DPS y devuelve el connection string listo.
    Retorna None si falla.
    """
    try:
        from azure.iot.device import ProvisioningDeviceClient
    except ImportError:
        logger.error("azure-iot-device no instalado. Ejecutar: pip install azure-iot-device")
        return None

    try:
        client = ProvisioningDeviceClient.create_from_symmetric_key(
            provisioning_host=DPS_HOST,
            registration_id=device_id,
            id_scope=id_scope,
            symmetric_key=device_key,
        )
        result = client.register()
        hub = result.registration_state.assigned_hub
        conn_str = (
            f"HostName={hub};"
            f"DeviceId={device_id};"
            f"SharedAccessKey={device_key}"
        )
        return conn_str
    except Exception as e:
        logger.error(f"Error registrando {device_id}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Provisiona los 10 dispositivos en Azure IoT Central via DPS"
    )
    parser.add_argument("--id-scope", default=os.getenv("DPS_ID_SCOPE"),
                        help="ID Scope de IoT Central (Administration → Device connection)")
    parser.add_argument("--master-key", default=os.getenv("DPS_MASTER_KEY"),
                        help="Primary Key maestra de IoT Central")
    parser.add_argument("--device-id", default=None,
                        help="Provisionar solo un dispositivo específico (ej: campus-ems-01)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Segundos de espera entre registros (evita throttle DPS)")
    args = parser.parse_args()

    if not args.id_scope:
        logger.error("Falta DPS_ID_SCOPE. Pasar con --id-scope o en variable de entorno.")
        sys.exit(1)
    if not args.master_key:
        logger.error("Falta DPS_MASTER_KEY. Pasar con --master-key o en variable de entorno.")
        sys.exit(1)

    devices_to_provision = DEVICES
    if args.device_id:
        devices_to_provision = [d for d in DEVICES if d["id"] == args.device_id]
        if not devices_to_provision:
            logger.error(f"Device ID '{args.device_id}' no está en la lista de dispositivos.")
            sys.exit(1)

    results = {}
    logger.info(f"Provisionando {len(devices_to_provision)} dispositivo(s)...")
    logger.info(f"ID Scope: {args.id_scope}")
    logger.info("=" * 60)

    for dev in devices_to_provision:
        device_id = dev["id"]
        label = dev["label"]
        logger.info(f"Registrando {label} ({device_id})...")

        device_key = derive_device_key(args.master_key, device_id)
        conn_str = provision_device(args.id_scope, device_id, device_key)

        if conn_str:
            results[device_id] = conn_str
            logger.info(f"OK: {device_id}")
        else:
            results[device_id] = None
            logger.warning(f"FALLO: {device_id}")

        if len(devices_to_provision) > 1:
            time.sleep(args.delay)

    # Imprimir bloque .env listo para copiar
    print("\n" + "=" * 60)
    print("# COPIAR AL ARCHIVO .env")
    print("=" * 60)
    print(f"DPS_ID_SCOPE={args.id_scope}")
    print()

    ok_count = 0
    fail_count = 0
    for dev in devices_to_provision:
        device_id = dev["id"]
        label = dev["label"]
        conn = results.get(device_id)
        if conn:
            ok_count += 1
            if device_id == "campus-ems-01":
                print(f"# {label}")
                print(f"IOT_CENTRAL_DPS_CONNECTION_STRING={conn}")
                print()
            elif device_id == "campus-ems-02":
                print(f"# {label} — mismo connection string para el bridge")
                print(f"# Reemplazar IOT_CENTRAL_DPS_CONNECTION_STRING si D2 corre en equipo separado")
                print()
            elif device_id == "campus-ems-03":
                print(f"# {label} — D3 usa variable de nombre distinto")
                print(f"IOT_CENTRAL_DPS_CONNECTION={conn}")
                print()
            elif device_id == "campus-ems-08":
                print(f"# {label}")
                print(f"AZURE_CONNECTION_STRING={conn}")
                print()
            else:
                # Los demás usan la misma var IOT_CENTRAL_DPS_CONNECTION_STRING
                # pero con distinto DEVICE_ID — la connection string va por separado en .env
                idx = device_id.replace("campus-ems-", "D")
                print(f"# {label}")
                print(f"# Usar esta connection string cuando corras {idx}:")
                print(f"# IOT_CENTRAL_DPS_CONNECTION_STRING={conn}")
                print()
        else:
            fail_count += 1
            print(f"# {label} — FALLO al provisionar")
            print()

    print("=" * 60)
    print(f"Resultado: {ok_count} OK, {fail_count} fallidos de {len(devices_to_provision)}")
    print("=" * 60)

    if fail_count > 0:
        print("\nDISPOSITIVOS FALLIDOS:")
        print("  - Verificar que el dispositivo esté registrado en IoT Central.")
        print("  - Verificar que la plantilla campus-emergency-v1 esté publicada.")
        print("  - Verificar DPS_ID_SCOPE y DPS_MASTER_KEY.")


if __name__ == "__main__":
    main()
