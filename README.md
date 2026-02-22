# Helios Smart Home CLI

CLI-Tool zur lokalen Steuerung von **Shelly Geräten (Gen 2/3)** (z.B. Plug S, 1 Mini Gen3) über die Shelly RPC-API. Entwickelt als Schnittstelle für KI-Agenten — alle Ausgaben sind maschinenlesbar (JSON auf stdout, Fehler auf stderr).

## Unterstützte Geräte

- **Shelly Plug S Gen 3 / Plus Plug S** (Schalten, Messen, LED)
- **Shelly 1 Mini Gen 3** (Schalten, kein Messen, keine LED)
- Generell alle Gen 2/3 Geräte mit `Switch` Komponente

## Voraussetzungen

- Python 3.10+
- `requests` — `pip install requests`
- Shelly Geräte müssen im selben lokalen Netzwerk erreichbar sein

## Installation

```bash
git clone https://github.com/agent-helios/helios-smart-home.git
cd helios-smart-home
pip install requests
```

## Schnellstart

```bash
# Gerät hinzufügen (Alias "lampe" für IP)
python smarthome.py add 192.168.1.50 lampe

# Einschalten
python smarthome.py on lampe

# Status abfragen
python smarthome.py status lampe

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
| `status <ziel>` | Status abfragen (Ein/Aus, Leistung in Watt*, Energie*) |
| `led <ziel> <mode>` | LED-Modus setzen: `switch`, `power` oder `off` (nur Plugs) |
| `list` | Alle Geräte und Gruppen anzeigen |

*\*Falls vom Gerät unterstützt (z.B. Plug S)*

## Ziel-Auflösung

Das `<ziel>`-Argument wird automatisch aufgelöst:

1. `all` — alle registrierten Geräte
2. **Gruppenname** — alle Mitglieder der Gruppe
3. **Alias** — z.B. `lampe`, `drucker`
4. **Hardware-ID** — direkte Zuordnung

## Datenstruktur

Geräte und Gruppen werden in `mappings.json` neben dem Skript gespeichert:

```json
{
  "devices": {
    "shellyplugsg3-abc123": { "ip": "192.168.1.50", "alias": "lampe", "model": "SNSN-0013A" }
  },
  "groups": {
    "wohnzimmer": ["lampe"]
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
    "alias": "lampe",
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
