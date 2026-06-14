REFRESH_INTERVAL = 30

CSS = """
Screen {
    background: #0a0a0a;
    color: #00ff00;
    layers: base overlay;
}

#status-bar {
    height: 1;
    background: #111111;
    color: #00ff00;
    padding: 0 1;
}

#net-table {
    height: 1fr;
    background: #0a0a0a;
    scrollbar-color: #003300;
    scrollbar-background: #0a0a0a;
}

DataTable > .datatable--header {
    background: #001a00;
    color: #00cc00;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #003300;
    color: #00ff00;
    text-style: bold;
}

DataTable > .datatable--hover {
    background: #001500;
}

#msg-bar {
    height: 1;
    background: #111111;
    padding: 0 1;
}

#footer {
    height: 1;
    background: #001a00;
    color: #007700;
    padding: 0 1;
}

PasswordModal {
    align: center middle;
}

#modal-box {
    width: 52;
    height: auto;
    background: #0a0a0a;
    border: solid #00ff00;
    padding: 1 2;
    align: center middle;
}

#modal-title {
    height: 2;
    color: #00ff00;
    content-align: center middle;
    text-style: bold;
}

#pwd-input {
    background: #001a00;
    border: solid #006600;
    color: #00ff00;
}

Input:focus {
    border: solid #00ff00;
}
"""
