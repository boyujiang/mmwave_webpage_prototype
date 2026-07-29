# Standalone MQTT Simulator

This folder is isolated from the Django application. It publishes the exact
message shape consumed by `analytics/management/commands/runmqtt.py`:

```text
esp/room/<room_number>/vitals
```

Run from the repository root with the existing virtual environment:

```powershell
# Preview without a broker
.\venv\Scripts\python.exe -m mqtt_simulator.publisher --dry-run --count 3

# Continuously publish for room 101
.\venv\Scripts\python.exe -m mqtt_simulator.publisher --room 101

# Publish ten mixed cycles for two rooms
.\venv\Scripts\python.exe -m mqtt_simulator.publisher `
  --room 101 --room 102 --scenario mixed --count 10

# Force the consumer's fall condition
.\venv\Scripts\python.exe -m mqtt_simulator.publisher `
  --room 101 --scenario fall
```

The publisher uses `127.0.0.1:1883` by default. `--host`, `--port`,
`--username`, and `--password` can override the broker connection.

## Broker test orchestrator

The orchestrator creates a temporary MQTT subscriber, runs one publishing
cycle, and checks that every room's topic arrives with a valid payload:

```powershell
.\venv\Scripts\python.exe -m mqtt_simulator.orchestrator `
  --room 101 --room 102
```

This verifies the simulator-to-broker portion. To exercise the complete
application path, keep the project's existing `runmqtt`, Redis, Django, and
frontend processes running while using the publisher.

## Unit tests

```powershell
.\venv\Scripts\python.exe -m unittest mqtt_simulator.test_simulator -v
```
