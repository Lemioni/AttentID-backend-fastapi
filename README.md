# Raspberry Pi MQTT Data Collection System

A FastAPI application that collects and processes data from Raspberry Pi devices via MQTT and stores it in a PostgreSQL database.

## Architecture

This system consists of:

1. **PostgreSQL Database** - For storing device information, location data, and MQTT messages
2. **pgAdmin** - For easy database inspection and management
3. **FastAPI Application** - RESTful API with endpoints to manage devices, locations, and MQTT data
4. **MQTT Client** - For subscribing to topics and receiving messages from Raspberry Pi devices

## Features

- Docker Compose setup for easy deployment
- PostgreSQL database with comprehensive data model
- MQTT message processing and storage
- REST API for data access and management
- Environment-based configuration

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Git

### Setup

1. Clone the repository:

```bash
git clone <your-repository-url>
cd <repository-name>
```

2. Create a `.env` file with your configuration (see `.env.example` for reference)

3. Start the Docker containers:

```bash
docker-compose up -d
```

4. The API will be available at: http://localhost:8000
5. API documentation is available at: http://localhost:8000/docs
6. pgAdmin will be available at: http://localhost:5050 (login with the credentials set in your `.env` file)

## API Endpoints

### Device Management

- `POST /device/register` - Register a new Raspberry Pi device
- `GET /device/{device_id}` - Get device details
- `GET /device/` - List all devices with optional filters
- `PUT /device/{device_id}` - Update device information
- `DELETE /device/{device_id}` - Delete a device

### MQTT Messages

- `POST /mqtt/receive` - Manually receive an MQTT message (for testing)
- `GET /mqtt/messages` - Get MQTT messages with optional filters
- `GET /mqtt/topics` - List all topics
- `POST /mqtt/publish` - Publish an MQTT message (for testing)

### Location Management

- `POST /location/type` - Create a new location type
- `GET /location/types` - List all location types
- `POST /location/` - Create a new location
- `GET /location/` - List all locations with optional filters
- `GET /location/{location_id}` - Get location details
- `DELETE /location/{location_id}` - Delete a location

## Environment Variables

Configuration is done through environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `MQTT_BROKER_HOST` - MQTT broker hostname/IP
- `MQTT_BROKER_PORT` - MQTT broker port
- `MQTT_CLIENT_ID` - MQTT client ID
- `MQTT_TOPIC` - MQTT topic pattern to subscribe to

## Contributing

Feel free to submit issues or pull requests for enhancements or fixes.

## License

[Your License Here]
