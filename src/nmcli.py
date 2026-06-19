import subprocess
from dataclasses import dataclass


@dataclass
class WifiNetwork:
    ssid: str
    signal: int
    security: str
    in_use: bool
    saved: bool = False


@dataclass
class DeviceStatus:
    device: str
    type: str
    state: str
    connection: str


def _parse_terse(line: str) -> list[str]:
    parts = []
    current = []
    i = 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line):
            current.append(line[i + 1])
            i += 2
        elif line[i] == ":":
            parts.append("".join(current))
            current = []
            i += 1
        else:
            current.append(line[i])
            i += 1
    parts.append("".join(current))
    return parts


def get_saved_connections() -> dict[str, str]:
    r = subprocess.run(
        ["nmcli", "-t", "-e", "yes", "-f", "NAME,TYPE", "con", "show"],
        capture_output=True, text=True,
    )
    connections = {}
    for line in r.stdout.strip().splitlines():
        if not line:
            continue
        parts = _parse_terse(line)
        if len(parts) >= 2 and "wireless" in parts[1]:
            name = parts[0]
            r2 = subprocess.run(
                ["nmcli", "-t", "-e", "yes", "-f", "802-11-wireless.ssid", "con", "show", name],
                capture_output=True, text=True,
            )
            for l in r2.stdout.strip().splitlines():
                p = _parse_terse(l)
                if len(p) >= 2 and p[1]:
                    connections[p[1]] = name
    return connections


def get_saved_ssids() -> set[str]:
    return set(get_saved_connections().keys())


def get_wifi_networks() -> list[WifiNetwork]:
    r = subprocess.run(
        ["nmcli", "-t", "-e", "yes", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
         "dev", "wifi", "list", "--rescan", "no"],
        capture_output=True, text=True,
    )
    saved = get_saved_ssids()
    networks = []
    seen: set[str] = set()
    for line in r.stdout.strip().splitlines():
        if not line:
            continue
        parts = _parse_terse(line)
        if len(parts) < 4:
            continue
        in_use = parts[0].strip() == "*"
        ssid = parts[1]
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        try:
            signal = int(parts[2])
        except ValueError:
            signal = 0
        security = parts[3] if parts[3] and parts[3] != "--" else "Open"
        networks.append(WifiNetwork(
            ssid=ssid,
            signal=signal,
            security=security,
            in_use=in_use,
            saved=ssid in saved,
        ))
    networks.sort(key=lambda n: (-int(n.in_use), -n.signal))
    return networks


def get_device_status() -> list[DeviceStatus]:
    r = subprocess.run(
        ["nmcli", "-t", "-e", "yes", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev", "status"],
        capture_output=True, text=True,
    )
    devices = []
    for line in r.stdout.strip().splitlines():
        if not line:
            continue
        parts = _parse_terse(line)
        if len(parts) >= 4:
            devices.append(DeviceStatus(*parts[:4]))
    return devices


def get_wifi_interface() -> str:
    for d in get_device_status():
        if d.type == "wifi":
            return d.device
    return "wlan0"


def get_ethernet_device() -> DeviceStatus | None:
    for d in get_device_status():
        if "ethernet" in d.type:
            return d
    return None


def get_current_ip(interface: str) -> str:
    r = subprocess.run(
        ["nmcli", "-t", "-f", "IP4.ADDRESS", "dev", "show", interface],
        capture_output=True, text=True,
    )
    for line in r.stdout.strip().splitlines():
        if "IP4.ADDRESS" in line:
            parts = line.split(":")
            if len(parts) >= 2:
                return parts[1].split("/")[0]
    return ""


def connect_wifi(ssid: str, password: str = "") -> tuple[bool, str]:
    saved = get_saved_connections()
    if ssid in saved:
        cmd = ["nmcli", "con", "up", saved[ssid]]
    elif password:
        cmd = ["nmcli", "dev", "wifi", "connect", ssid, "password", password]
    else:
        cmd = ["nmcli", "dev", "wifi", "connect", ssid]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip() or r.stdout.strip()


def disconnect(interface: str) -> tuple[bool, str]:
    r = subprocess.run(
        ["nmcli", "dev", "disconnect", interface],
        capture_output=True, text=True,
    )
    return r.returncode == 0, r.stderr.strip()


def forget_network(ssid: str) -> tuple[bool, str]:
    saved = get_saved_connections()
    name = saved.get(ssid, ssid)
    r = subprocess.run(
        ["nmcli", "con", "delete", name],
        capture_output=True, text=True,
    )
    return r.returncode == 0, r.stderr.strip()


def connect_ethernet() -> tuple[bool, str]:
    eth = get_ethernet_device()
    if not eth:
        return False, "No ethernet device found"
    r = subprocess.run(
        ["nmcli", "dev", "connect", eth.device],
        capture_output=True, text=True,
    )
    return r.returncode == 0, r.stderr.strip()


def rescan() -> None:
    subprocess.run(["nmcli", "dev", "wifi", "rescan"], capture_output=True, text=True)


def signal_bars(signal: int) -> str:
    if signal >= 75:
        return "▂▄▆█"
    elif signal >= 50:
        return "▂▄▆░"
    elif signal >= 25:
        return "▂▄░░"
    else:
        return "▂░░░"
