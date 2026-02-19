#!/usr/bin/env python3
"""CLI interface for managing Shelly Plug S (Gen 2/3) smart plugs via local HTTP API."""

import argparse
import json
import sys
from pathlib import Path

import requests

MAPPINGS_FILE = Path(__file__).parent / "mappings.json"
REQUEST_TIMEOUT = 5


# ─── Persistence ────────────────────────────────────────────────────────────────

def load_mappings() -> dict:
    """Load device/group mappings from disk. Returns empty structure if file missing."""
    if MAPPINGS_FILE.exists():
        return json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))
    return {"devices": {}, "groups": {}}


def save_mappings(data: dict) -> None:
    """Persist device/group mappings to disk."""
    MAPPINGS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ─── Target Resolution ──────────────────────────────────────────────────────────

def resolve_targets(data: dict, target: str) -> list[dict]:
    """Resolve a target string to a list of device dicts with keys 'hw_id', 'ip', 'alias'.

    Resolution order: 'all' -> group name -> alias -> hardware_id.
    Prints warnings to stderr for unresolvable targets.
    """
    devices = data["devices"]
    groups = data["groups"]

    if target == "all":
        return [{"hw_id": k, **v} for k, v in devices.items()]

    if target in groups:
        results = []
        for member in groups[target]:
            resolved = _resolve_single(devices, member)
            if resolved:
                results.append(resolved)
            else:
                print(f"WARNING: group member '{member}' could not be resolved, skipping", file=sys.stderr)
        return results

    single = _resolve_single(devices, target)
    if single:
        return [single]

    print(f"ERROR: target '{target}' not found as alias, hardware_id, or group", file=sys.stderr)
    sys.exit(1)


def _resolve_single(devices: dict, identifier: str) -> dict | None:
    """Resolve a single identifier (alias or hardware_id) to a device dict."""
    # Check alias first
    for hw_id, info in devices.items():
        if info.get("alias") == identifier:
            return {"hw_id": hw_id, **info}
    # Check hardware_id
    if identifier in devices:
        return {"hw_id": identifier, **devices[identifier]}
    return None


def resolve_single_device(data: dict, target: str) -> dict:
    """Resolve target to exactly one device. Exit on ambiguity or miss."""
    results = resolve_targets(data, target)
    if len(results) != 1:
        print(f"ERROR: expected exactly one device for '{target}', got {len(results)}", file=sys.stderr)
        sys.exit(1)
    return results[0]


# ─── HTTP helpers ────────────────────────────────────────────────────────────────

def shelly_get(ip: str, path: str) -> dict | None:
    """Send a GET request to a Shelly device. Returns parsed JSON or None on failure."""
    url = f"http://{ip}{path}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"ERROR: request to {url} failed: {exc}", file=sys.stderr)
        return None


def shelly_post(ip: str, path: str, payload: dict) -> dict | None:
    """Send a POST request with JSON body to a Shelly device."""
    url = f"http://{ip}{path}"
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        print(f"ERROR: request to {url} failed: {exc}", file=sys.stderr)
        return None


# ─── Device Management ───────────────────────────────────────────────────────────

def cmd_add(args: argparse.Namespace) -> None:
    """Add a Shelly device by IP. Queries the device for its hardware ID and stores it."""
    info = shelly_get(args.ip, "/rpc/Shelly.GetDeviceInfo")
    if info is None:
        print(f"ERROR: could not reach device at {args.ip}", file=sys.stderr)
        sys.exit(1)

    hw_id = info.get("id")
    if not hw_id:
        print("ERROR: device response missing 'id' field", file=sys.stderr)
        sys.exit(1)

    data = load_mappings()
    alias = str(args.alias) if args.alias is not None else ""
    data["devices"][hw_id] = {"ip": args.ip, "alias": alias}
    save_mappings(data)
    print(json.dumps({"ok": True, "hw_id": hw_id, "ip": args.ip, "alias": alias}))


def cmd_remove(args: argparse.Namespace) -> None:
    """Remove a device from mappings and all groups."""
    data = load_mappings()
    dev = resolve_single_device(data, args.target)
    hw_id = dev["hw_id"]

    del data["devices"][hw_id]
    for members in data["groups"].values():
        members[:] = [m for m in members if m != hw_id and m != dev.get("alias")]
    save_mappings(data)
    print(json.dumps({"ok": True, "removed": hw_id}))


def cmd_rename(args: argparse.Namespace) -> None:
    """Update the alias of an existing device."""
    data = load_mappings()
    dev = resolve_single_device(data, args.target)
    data["devices"][dev["hw_id"]]["alias"] = str(args.new_alias)
    save_mappings(data)
    print(json.dumps({"ok": True, "hw_id": dev["hw_id"], "alias": str(args.new_alias)}))


# ─── Group Management ────────────────────────────────────────────────────────────

def cmd_group(args: argparse.Namespace) -> None:
    """Dispatch group sub-commands."""
    data = load_mappings()

    if args.group_action == "create":
        if args.group_name in data["groups"]:
            print(f"ERROR: group '{args.group_name}' already exists", file=sys.stderr)
            sys.exit(1)
        data["groups"][args.group_name] = []
        save_mappings(data)
        print(json.dumps({"ok": True, "created": args.group_name}))

    elif args.group_action == "delete":
        if args.group_name not in data["groups"]:
            print(f"ERROR: group '{args.group_name}' not found", file=sys.stderr)
            sys.exit(1)
        del data["groups"][args.group_name]
        save_mappings(data)
        print(json.dumps({"ok": True, "deleted": args.group_name}))

    elif args.group_action == "add":
        if args.group_name not in data["groups"]:
            print(f"ERROR: group '{args.group_name}' not found", file=sys.stderr)
            sys.exit(1)
        targets = resolve_targets(data, args.target)
        added = []
        for dev in targets:
            identifier = dev["alias"] if dev.get("alias") else dev["hw_id"]
            if identifier not in data["groups"][args.group_name]:
                data["groups"][args.group_name].append(identifier)
                added.append(identifier)
        save_mappings(data)
        print(json.dumps({"ok": True, "group": args.group_name, "added": added}))

    elif args.group_action == "remove":
        if args.group_name not in data["groups"]:
            print(f"ERROR: group '{args.group_name}' not found", file=sys.stderr)
            sys.exit(1)
        targets = resolve_targets(data, args.target)
        removed = []
        for dev in targets:
            members = data["groups"][args.group_name]
            for ident in (dev.get("alias"), dev["hw_id"]):
                if ident and ident in members:
                    members.remove(ident)
                    removed.append(ident)
        save_mappings(data)
        print(json.dumps({"ok": True, "group": args.group_name, "removed": removed}))


# ─── Actions ─────────────────────────────────────────────────────────────────────

def cmd_on(args: argparse.Namespace) -> None:
    """Turn on relay for target device(s)."""
    data = load_mappings()
    results = []
    for dev in resolve_targets(data, args.target):
        resp = shelly_get(dev["ip"], "/rpc/Switch.Set?id=0&on=true")
        results.append({"hw_id": dev["hw_id"], "alias": dev.get("alias", ""), "success": resp is not None})
    print(json.dumps(results))


def cmd_off(args: argparse.Namespace) -> None:
    """Turn off relay for target device(s)."""
    data = load_mappings()
    results = []
    for dev in resolve_targets(data, args.target):
        resp = shelly_get(dev["ip"], "/rpc/Switch.Set?id=0&on=false")
        results.append({"hw_id": dev["hw_id"], "alias": dev.get("alias", ""), "success": resp is not None})
    print(json.dumps(results))


def cmd_toggle(args: argparse.Namespace) -> None:
    """Toggle relay for target device(s)."""
    data = load_mappings()
    results = []
    for dev in resolve_targets(data, args.target):
        resp = shelly_get(dev["ip"], "/rpc/Switch.Toggle?id=0")
        results.append({"hw_id": dev["hw_id"], "alias": dev.get("alias", ""), "success": resp is not None})
    print(json.dumps(results))


def cmd_status(args: argparse.Namespace) -> None:
    """Query switch status (output state, power, energy) for target device(s)."""
    data = load_mappings()
    results = []
    for dev in resolve_targets(data, args.target):
        resp = shelly_get(dev["ip"], "/rpc/Switch.GetStatus?id=0")
        entry = {"hw_id": dev["hw_id"], "alias": dev.get("alias", ""), "online": resp is not None}
        if resp is not None:
            entry["output"] = resp.get("output")
            entry["apower"] = resp.get("apower")
            entry["aenergy_total"] = resp.get("aenergy", {}).get("total")
        results.append(entry)
    print(json.dumps(results))


def cmd_led(args: argparse.Namespace) -> None:
    """Set LED ring mode for target device(s)."""
    valid_modes = ("switch", "power", "off")
    if args.mode not in valid_modes:
        print(f"ERROR: invalid LED mode '{args.mode}', must be one of {valid_modes}", file=sys.stderr)
        sys.exit(1)

    data = load_mappings()
    payload = {"config": {"leds": {"mode": args.mode}}}
    results = []
    for dev in resolve_targets(data, args.target):
        resp = shelly_post(dev["ip"], "/rpc/PLUGS_UI.SetConfig", payload)
        results.append({"hw_id": dev["hw_id"], "alias": dev.get("alias", ""), "success": resp is not None})
    print(json.dumps(results))


# ─── List ────────────────────────────────────────────────────────────────────────

def cmd_list(_args: argparse.Namespace) -> None:
    """List all registered devices and groups from mappings."""
    data = load_mappings()
    print(json.dumps(data, indent=2))


# ─── CLI Parser ──────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(description="Shelly Plug S (Gen2/3) local network CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a device by IP")
    p_add.add_argument("ip", help="Device IP address")
    p_add.add_argument("alias", nargs="?", default=None, help="Optional alias (treated as string)")

    # remove
    p_rm = sub.add_parser("remove", help="Remove a device")
    p_rm.add_argument("target", help="Alias, hardware_id, or group")

    # rename
    p_ren = sub.add_parser("rename", help="Rename a device alias")
    p_ren.add_argument("target", help="Current alias or hardware_id")
    p_ren.add_argument("new_alias", help="New alias (treated as string)")

    # group
    p_grp = sub.add_parser("group", help="Group management")
    grp_sub = p_grp.add_subparsers(dest="group_action", required=True)

    p_gc = grp_sub.add_parser("create", help="Create an empty group")
    p_gc.add_argument("group_name")

    p_gd = grp_sub.add_parser("delete", help="Delete a group")
    p_gd.add_argument("group_name")

    p_ga = grp_sub.add_parser("add", help="Add device(s) to a group")
    p_ga.add_argument("group_name")
    p_ga.add_argument("target", help="Device alias, hardware_id, group, or 'all'")

    p_gr = grp_sub.add_parser("remove", help="Remove device(s) from a group")
    p_gr.add_argument("group_name")
    p_gr.add_argument("target", help="Device alias, hardware_id, group, or 'all'")

    # on / off / toggle
    for name in ("on", "off", "toggle"):
        p = sub.add_parser(name, help=f"Turn {name} target device(s)")
        p.add_argument("target", help="Alias, hardware_id, group, or 'all'")

    # status
    p_st = sub.add_parser("status", help="Query device status")
    p_st.add_argument("target", help="Alias, hardware_id, group, or 'all'")

    # led
    p_led = sub.add_parser("led", help="Set LED ring mode")
    p_led.add_argument("target", help="Alias, hardware_id, group, or 'all'")
    p_led.add_argument("mode", choices=["switch", "power", "off"], help="LED mode")

    # list
    sub.add_parser("list", help="List all devices and groups")

    return parser


def main() -> None:
    """Entry point — parse args and dispatch to the matching command handler."""
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "add": cmd_add,
        "remove": cmd_remove,
        "rename": cmd_rename,
        "group": cmd_group,
        "on": cmd_on,
        "off": cmd_off,
        "toggle": cmd_toggle,
        "status": cmd_status,
        "led": cmd_led,
        "list": cmd_list,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
