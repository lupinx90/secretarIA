# secretarIA

Control de elementos personales (sueño, agenda y habla).

## Envío del estado de red a manIA

secretarIA comprueba las direcciones IPv4 definidas en `IP_TARGETS` y envía a
manIA un informe JSON en cada ciclo de `CHECK_INTERVAL`. Configura en `.env` la
URL privada de manIA:

```dotenv
MANIA_STATUS_API_URL=http://127.0.0.1:8000/api/network-status
```

El informe tiene este formato:

```json
{
  "targets": [
    {"ip": "192.168.1.10", "online": true},
    {"ip": "192.168.1.11", "online": false}
  ]
}
```

manIA admite hasta 64 direcciones IPv4 por informe. Su endpoint no requiere
autenticación; mantén manIA accesible solo desde una red privada de confianza
y no publiques esta URL en Internet. manIA almacena el último informe completo
recibido y no combina informes de distintos emisores. Usa un único emisor para
todos los targets que quieras mostrar en manIA.

Después de configurar `.env`, recrea el contenedor:

```bash
docker compose up --build -d
```
