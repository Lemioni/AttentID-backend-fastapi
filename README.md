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

### Autentizační Endpointy

- **Registrace uživatele**
  - `POST /api/auth/register`
  - Popis: Registruje nového uživatele v systému.
  - Request Body (JSON):
    ```json
    {
      "email": "uzivatel@example.com",
      "password": "supertajneheslo",
      "name": "Jan Novák"
    }
    ```
  - Úspěšná odpověď (201 Created):
    ```json
    {
      "message": "Registrace úspěšná.",
      "user": {
        "id_users": 1,
        "email": "uzivatel@example.com",
        "name": "Jan Novák",
        "created": "2023-10-28T10:00:00Z"
      }
    }
    ```

- **Přihlášení uživatele**
  - `POST /api/auth/login`
  - Popis: Přihlásí existujícího uživatele a vrátí JWT token.
  - Request Body (JSON):
    ```json
    {
      "email": "uzivatel@example.com",
      "password": "supertajneheslo"
    }
    ```
  - Úspěšná odpověď (200 OK):
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```
  - Chybná odpověď (401 Unauthorized):
    ```json
    {
      "detail": "Nesprávné přihlašovací údaje."
    }
    ```
- **Získání informací o přihlášeném uživateli**
  - `GET /api/users/me`
  - Popis: Získání informací o přihlášeném uživateli (Gets information about the logged-in user).
  - Autentizace: Vyžadována.
  - Databázové akce: Načte data z `users` a připojených `user_role` &amp; `roles` pro autentizovaného uživatele (Loads data from `users` and joined `user_role` &amp; `roles` for the authenticated user).
  - Ideální JSON odpověď (200 OK):
    ```json
    {
      "id_users": 1,
      "name": "Jan Novák",
      "email": "uzivatel@example.com",
      "created": "2023-10-26T10:00:00Z",
      "last_active": "2023-10-28T09:15:00Z",
      "roles": [
        {"id_roles": 1, "description": "uzivatel"}
      ]
    }
    ```

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