---
name: smart-home
description: Control Shelly smart devices (Gen 2/3) like Plug S and 1 Mini - turn lights/devices on or off, toggle, check power usage and energy consumption (where supported), manage device aliases and groups. Use when Moritz wants to control smart home devices, check if something is on or off, measure power draw, or manage his Shelly devices.
---

# Smart Home Skill

Controls Shelly Gen 2/3 devices (Plug S, 1 Mini, etc.) via local HTTP API.
Backed by [helios-smart-home](https://github.com/agent-helios/helios-smart-home).

## Script

```bash
python3 ~/.openclaw/workspace/skills/smart-home/smarthome.py <command> [args]
```

Device mappings are stored in `mappings.json` (next to the script). Shelly devices must be reachable on the local network.

## Commands

### Control
```bash
python3 smarthome.py on <target>       # turn on
python3 smarthome.py off <target>      # turn off
python3 smarthome.py toggle <target>   # toggle
python3 smarthome.py status <target>   # output state, power (W)*, energy (Wh)*
```
*\*Power/Energy only available on devices with metering (e.g. Plug S).*

### Device Management
```bash
python3 smarthome.py list                        # show all devices + groups
python3 smarthome.py add <ip> [alias]            # add device (auto-fetches hw_id)
python3 smarthome.py remove <target>             # remove device
python3 smarthome.py rename <target> <new_alias> # rename alias
```

### Groups
```bash
python3 smarthome.py group create <name>
python3 smarthome.py group add <name> <target>
python3 smarthome.py group remove <name> <target>
python3 smarthome.py group delete <name>
```

## Target Resolution

`<target>` resolves in order: `all` → group name → alias → hardware_id

## Output Format

stdout: JSON (always). stderr: errors/warnings.

Status example (Plug S):
```json
[{"hw_id": "shellyplugsg3-abc123", "alias": "schreibtisch", "online": true, "output": true, "apower": 42.5, "aenergy_total": 1234.56}]
```

Status example (1 Mini):
```json
[{"hw_id": "shelly1minig3-xyz789", "alias": "deckenlicht", "online": true, "output": false}]
```

## Usage Notes

- **Complex requests:** If Moritz asks for "relaxed light in living room" (intersection of groups), first run `list` to see group members, manually calculate the intersection/target devices, then call `on/off` for the specific device aliases.
- Present power in a human-friendly way: `42.5 W`, energy as `1.23 kWh` (only if available in JSON)
- If a device is unreachable, `online: false` — tell Moritz it's offline
- `alias` is the friendly name (e.g. "schreibtisch", "drucker", "1"); prefer using aliases over hw_ids
- Before first use: add devices with `add <ip> <alias>`
