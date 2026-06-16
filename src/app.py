from textual.app import App, ComposeResult
from textual.widgets import DataTable, Static, Input
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.binding import Binding
from textual import work
import threading
from . import nmcli as nm
from .config import CSS


class PasswordModal(ModalScreen):
    BINDINGS = [("escape", "app.pop_screen", "Cancel")]

    def __init__(self, ssid: str):
        super().__init__()
        self.ssid = ssid

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Static(f"Connect to: [bold]{self.ssid}[/]", id="modal-title")
            yield Input(placeholder="password", password=True, id="pwd-input")

    def on_mount(self):
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        self.dismiss(event.value)


class NetApp(App):
    CSS = CSS

    BINDINGS = [
        Binding("j", "cursor_down", show=False),
        Binding("k", "cursor_up", show=False),
        Binding("g", "cursor_top", show=False),
        Binding("G", "cursor_bottom", show=False),
        Binding("d", "disconnect", "Disconnect", show=False),
        Binding("D", "forget", "Forget", show=False),
        Binding("e", "ethernet", "Ethernet", show=False),
        Binding("r", "rescan", "Rescan", show=False),
        Binding("q", "quit", "Quit", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.networks: list[nm.WifiNetwork] = []
        self._stop_event = threading.Event()

    def compose(self) -> ComposeResult:
        yield Static("", id="status-bar")
        yield DataTable(id="net-table", cursor_type="row", show_cursor=True)
        yield Static("", id="msg-bar")
        yield Static(
            " [bold]Enter[/]:connect  [bold]d[/]:disconnect  [bold]D[/]:forget"
            "  [bold]e[/]:ethernet  [bold]r[/]:rescan  [bold]q[/]:quit",
            id="footer",
        )

    def on_mount(self):
        table = self.query_one(DataTable)
        table.add_columns("", "SSID", "Signal", "Security", "Saved")
        table.focus()
        self._load_networks_bg()
        self._start_auto_refresh()

    @work(thread=True)
    def _load_networks_bg(self):
        networks = nm.get_wifi_networks()
        self.call_from_thread(self._apply_networks, networks)

    def _apply_networks(self, networks):
        self.networks = networks
        self._update_status()
        self._populate_table()

    def _load_networks(self):
        self._load_networks_bg()

    @work(thread=True)
    def _start_auto_refresh(self):
        while not self._stop_event.wait(30):
            self.call_from_thread(self._load_networks)

    def _update_status(self):
        devices = nm.get_device_status()
        wifi = next((d for d in devices if d.type == "wifi"), None)
        eth = next((d for d in devices if d.type == "ethernet"), None)
        parts = []
        if wifi and wifi.state == "connected":
            ip = nm.get_current_ip(wifi.device)
            parts.append(f"[green]WiFi:[/] {wifi.connection}  [dim]{ip}[/]")
        if eth and eth.state == "connected":
            ip = nm.get_current_ip(eth.device)
            parts.append(f"[cyan]ETH:[/] {eth.connection}  [dim]{ip}[/]")
        if not parts:
            parts.append("[red]Not connected[/]")
        self.query_one("#status-bar", Static).update("  ".join(parts))

    def _populate_table(self):
        table = self.query_one(DataTable)
        prev_row = table.cursor_row
        table.clear()
        for net in self.networks:
            marker = "[green]▶[/]" if net.in_use else " "
            bars = nm.signal_bars(net.signal)
            saved = "[cyan]✓[/]" if net.saved else ""
            table.add_row(marker, net.ssid, f"{bars} {net.signal}%", net.security, saved)
        if self.networks:
            table.move_cursor(row=min(prev_row, len(self.networks) - 1))

    def _msg(self, text: str, error: bool = False):
        color = "red" if error else "green"
        self.query_one("#msg-bar", Static).update(f"[{color}]{text}[/]")

    def _current_network(self) -> nm.WifiNetwork | None:
        if not self.networks:
            return None
        row = self.query_one(DataTable).cursor_row
        if 0 <= row < len(self.networks):
            return self.networks[row]
        return None

    def action_cursor_down(self):
        table = self.query_one(DataTable)
        table.move_cursor(row=min(table.cursor_row + 1, len(self.networks) - 1))

    def action_cursor_up(self):
        table = self.query_one(DataTable)
        table.move_cursor(row=max(table.cursor_row - 1, 0))

    def action_cursor_top(self):
        self.query_one(DataTable).move_cursor(row=0)

    def action_cursor_bottom(self):
        self.query_one(DataTable).move_cursor(row=max(len(self.networks) - 1, 0))

    def action_connect(self):
        net = self._current_network()
        if not net:
            return
        if net.in_use:
            self._msg(f"Already connected to {net.ssid}")
            return
        if net.saved or net.security == "Open":
            self._do_connect(net.ssid, "")
        else:
            def on_password(pwd):
                if pwd is not None:
                    self._do_connect(net.ssid, pwd)
            self.push_screen(PasswordModal(net.ssid), on_password)

    @work(thread=True)
    def _do_connect(self, ssid: str, password: str):
        self.call_from_thread(self._msg, f"Connecting to {ssid}…")
        ok, msg = nm.connect_wifi(ssid, password)
        if ok:
            self.call_from_thread(self._msg, f"Connected to {ssid}")
        else:
            self.call_from_thread(self._msg, f"Failed: {msg}", True)
        self.call_from_thread(self._load_networks)

    def action_disconnect(self):
        iface = nm.get_wifi_interface()
        ok, msg = nm.disconnect(iface)
        self._msg("Disconnected" if ok else msg, not ok)
        self._load_networks()

    def action_forget(self):
        net = self._current_network()
        if not net or not net.saved:
            self._msg("Network not saved", True)
            return
        ok, msg = nm.forget_network(net.ssid)
        self._msg(f"Forgot {net.ssid}" if ok else msg, not ok)
        self._load_networks()

    def action_ethernet(self):
        self._msg("Connecting ethernet…")
        ok, msg = nm.connect_ethernet()
        self._msg("Ethernet connected" if ok else msg, not ok)
        self._update_status()

    def action_rescan(self):
        self._do_rescan()

    @work(thread=True)
    def _do_rescan(self):
        self.call_from_thread(self._msg, "Scanning…")
        nm.rescan()
        self.call_from_thread(self._load_networks)
        self.call_from_thread(self._msg, "Scan complete")

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        self.action_connect()

    def action_quit(self):
        self._stop_event.set()
        self.exit()
