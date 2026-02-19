# Helios Smart Home CLI

CLI-Tool zur lokalen Steuerung von **Shelly Plug S Gen 3** und **Plus Plug S** Steckdosen über die Shelly RPC-API (Gen 2/3). Entwickelt als Schnittstelle für KI-Agenten — alle Ausgaben sind maschinenlesbar (JSON auf stdout, Fehler auf stderr).

## Voraussetzungen

- Python 3.10+
- `requests` — `pip install requests`
- Shelly Plugs müssen im selben lokalen Netzwerk erreichbar sein

## Installation

```bash
git clone https://github.com/Moritz/helios-smart-home.git
cd helios-smart-home
pip install requests
```

## Schnellstart

```bash
# Gerät hinzufügen (Alias "1" für physisch beschriftete Steckdose)
python smarthome.py add 192.168.1.50 1

# Einschalten
python smarthome.py on 1

# Status abfragen
python smarthome.py status 1

# Alle Geräte auflisten
python smarthome.py list
```

## Befehle

### Geräte-Management

| Befehl | Beschreibung |
|---|---|
| `add <ip> [alias]` | Gerät per IP hinzufügen, Hardware-ID wird automatisch abgefragt |
| `remove <ziel>` | Gerät entfernen (auch aus allen Gruppen) |
| `rename <ziel> <neues_alias>` | Alias eines Geräts ändern |

### Gruppen-Management

| Befehl | Beschreibung |
|---|---|
| `group create <name>` | Leere Gruppe anlegen |
| `group add <name> <ziel>` | Gerät(e) zur Gruppe hinzufügen |
| `group remove <name> <ziel>` | Gerät(e) aus Gruppe entfernen |
| `group delete <name>` | Gruppe löschen |

### Aktionen

| Befehl | Beschreibung |
|---|---|
| `on <ziel>` | Relais einschalten |
| `off <ziel>` | Relais ausschalten |
| `toggle <ziel>` | Relais-Zustand umschalten |
| `status <ziel>` | Status abfragen (Ein/Aus, Leistung in Watt, Energie) |
| `led <ziel> <mode>` | LED-Modus setzen: `switch`, `power` oder `off` |
| `list` | Alle Geräte und Gruppen anzeigen |

## Ziel-Auflösung

Das `<ziel>`-Argument wird automatisch aufgelöst:

1. `all` — alle registrierten Geräte
2. **Gruppenname** — alle Mitglieder der Gruppe
3. **Alias** — z.B. `1`, `2`, `Drucker`
4. **Hardware-ID** — direkte Zuordnung

## Datenstruktur

Geräte und Gruppen werden in `mappings.json` neben dem Skript gespeichert:

```json
{
  "devices": {
    "shellyplugsg3-abc123": { "ip": "192.168.1.50", "alias": "1" }
  },
  "groups": {
    "wohnzimmer": ["1", "2"]
  }
}
```

## Ausgabeformat

- **stdout** — JSON (maschinenlesbar für KI-Agenten)
- **stderr** — Fehler und Warnungen im Klartext

Beispiel `status`-Antwort:

```json
[
  {
    "hw_id": "shellyplugsg3-abc123",
    "alias": "1",
    "online": true,
    "output": true,
    "apower": 42.5,
    "aenergy_total": 1234.56
  }
]
```

## Fehlerbehandlung

- HTTP-Timeout: 5 Sekunden pro Gerät
- Bei Gruppen-Aufrufen werden fehlerhafte Geräte übersprungen (`"success": false`) statt das Skript abzubrechen
- Nicht erreichbare Geräte erzeugen Warnungen auf stderr
