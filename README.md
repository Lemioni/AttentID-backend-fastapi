# AttentID Backend FastAPI

Backendová aplikace pro zpracování a ukládání dat z BLE skenerů AttentID. Aplikace přijímá data přes MQTT protokol, zpracovává je a ukládá do PostgreSQL databáze.

## 🚀 Funkce

- Příjem BLE dat přes MQTT protokol
- Automatická detekce a registrace nových zařízení
- REST API pro přístup k datům
- Zabezpečené MQTT spojení přes TLS
- Automatické zpracování různých formátů dat
- Perzistentní ukládání do PostgreSQL

## 📁 Struktura projektu

```
app/
├── core/           # Jádro aplikace (databáze, DI container)
├── config/         # Konfigurační soubory
├── models/         # SQLAlchemy modely
├── mqtt/           # MQTT klient a zpracování zpráv
├── routes/         # API endpointy
├── schemas/        # Pydantic schémata
└── services/       # Byznys logika
```

### Klíčové komponenty

- `mqtt/client.py` - MQTT klient pro komunikaci s brokerem
- `mqtt/handler.py` - Zpracování MQTT zpráv a ukládání do DB
- `models/models.py` - Databázové modely (User, Device, Topic, atd.)
- `config/settings.py` - Konfigurační proměnné aplikace

## 🛠 Technologie

- FastAPI - Moderní, rychlý webový framework
- SQLAlchemy - ORM pro práci s databází
- Paho MQTT - Knihovna pro MQTT komunikaci
- PostgreSQL - Databázový systém
- Pydantic - Validace dat a nastavení

## 📦 Instalace

1. Klonování repozitáře:
```bash
git clone <repository-url>
cd AttentID-backend-fastapi
```

2. Instalace závislostí:
```bash
pip install -r requirements.txt
```

3. Nastavení prostředí:
   - Vytvořte soubor `.env` podle vzoru `.env.example`
   - Nastavte připojení k databázi a MQTT brokeru

4. Spuštění aplikace:
```bash
uvicorn app.main:app --reload
```

## ⚙️ Konfigurace

Hlavní konfigurační proměnné v `config/settings.py`:

- `DATABASE_URL` - URL pro připojení k PostgreSQL
- `MQTT_BROKER_HOST` - Adresa MQTT brokeru
- `MQTT_BROKER_PORT` - Port MQTT brokeru (8883 pro TLS)
- `MQTT_USERNAME` - Přihlašovací jméno pro MQTT
- `MQTT_PASSWORD` - Heslo pro MQTT
- `MQTT_TOPIC` - Téma pro odběr zpráv

## 📡 MQTT komunikace

### Formát zpráv

Aplikace podporuje dva formáty dat:

1. JSON formát:
```json
{
    "device_id": "AA:BB:CC:DD:EE:FF",
    "data": {
        "rssi": -75,
        "timestamp": "2024-03-14T12:00:00Z"
    }
}
```

2. Python dictionary formát (z BLE skenerů):
```python
{
    'mac': 'AA:BB:CC:DD:EE:FF',
    'data': {
        'rssi': -75,
        'timestamp': '2024-03-14T12:00:00Z'
    }
}
```

### Zpracování zpráv

1. Příjem zprávy přes MQTT
2. Parsování a extrakce device_id
3. Vytvoření nebo aktualizace záznamu zařízení
4. Uložení zprávy do databáze

## 🔄 API Endpointy

### MQTT Endpointy

- `POST /api/v1/mqtt/receive` - Manuální příjem MQTT zpráv
- `GET /api/v1/mqtt/messages` - Získání historie zpráv

### Databázové Endpointy

- `GET /api/v1/database/status` - Stav databáze
- `POST /api/v1/database/populate-all` - Naplnění testovacími daty

## 📊 Databázový model

Hlavní entity:
- `User` - Uživatelé systému
- `Device` - BLE zařízení
- `Topic` - MQTT témata
- `MQTTEntry` - Záznamy MQTT zpráv
- `Location` - Umístění zařízení
- `LocationType` - Typy umístění

## 🔒 Zabezpečení

- MQTT komunikace přes TLS
- CORS ochrana pro API
- Validace dat pomocí Pydantic
- Bezpečné ukládání citlivých údajů

## 🚦 Logování

Aplikace používá standardní Python logging:
- INFO úroveň pro běžné operace
- WARNING pro neočekávané situace
- ERROR pro chyby vyžadující pozornost