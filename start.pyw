"""
╔══════════════════════════════════════════════════════════════╗
║                    NEXUS CMS Launcher                       ║
║          Secure Startup Script with MAC Validation          ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import subprocess
import socket
import time
import uuid
import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser
import ctypes
import ctypes.wintypes

# ═══════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════

# Allowed MAC addresses (add your devices here)
ALLOWED_MACS = [
    "34-F3-9A-D4-53-B9",
    # Add more MAC addresses below:
    # "AA-BB-CC-DD-EE-FF",
]

# Server settings
SERVER_HOST = "0.0.0.0"
SERVER_PORT = "8000"
CUSTOM_DOMAIN = "altekia.fady"  # Custom LAN domain
BROWSER_URL = "http://localhost:8000"  # Will be updated dynamically

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = "python"
MANAGE_PY = os.path.join(BASE_DIR, "manage.py")


# ═══════════════════════════════════════════════════════════
# NETWORK UTILITIES
# ═══════════════════════════════════════════════════════════

def get_local_ip():
    """Get the local network IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def open_firewall_port():
    """Open ports 8000 and 53 in Windows Firewall so LAN devices can connect."""
    for port, proto, name in [
        ("8000", "TCP", "NEXUS CMS Port 8000"),
        ("53",   "UDP", "NEXUS CMS DNS Port 53"),
    ]:
        try:
            subprocess.run(
                [
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    f"name={name}",
                    "dir=in", "action=allow",
                    f"protocol={proto}", f"localport={port}"
                ],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# MINI DNS SERVER
# ═══════════════════════════════════════════════════════════

def _parse_dns_domain(data):
    """Extract domain name from a raw DNS query packet."""
    try:
        offset = 12
        labels = []
        while offset < len(data):
            length = data[offset]
            if length == 0:
                break
            offset += 1
            labels.append(data[offset:offset + length].decode('utf-8', errors='ignore'))
            offset += length
        return '.'.join(labels).lower()
    except Exception:
        return ''


def _build_dns_response(query, ip):
    """Build a DNS A-record response pointing to the given IP."""
    try:
        resp = bytearray(query[:2])          # transaction ID
        resp += b'\x84\x00'                  # flags: QR=1, AA=1, RCODE=0
        resp += query[4:6]                    # QDCOUNT
        resp += b'\x00\x01'                  # ANCOUNT = 1
        resp += b'\x00\x00\x00\x00'          # NSCOUNT, ARCOUNT
        # Question section (copy from query)
        q_start = 12
        q_end = q_start
        while q_end < len(query) and query[q_end] != 0:
            q_end += 1 + query[q_end]
        q_end += 5  # null + QTYPE + QCLASS
        resp += query[q_start:q_end]
        # Answer section
        resp += b'\xc0\x0c'                  # pointer to question name
        resp += b'\x00\x01'                  # type A
        resp += b'\x00\x01'                  # class IN
        resp += b'\x00\x00\x00\x3c'          # TTL 60 s
        resp += b'\x00\x04'                  # RDLENGTH
        resp += bytes(int(x) for x in ip.split('.'))
        return bytes(resp)
    except Exception:
        return None


def _forward_dns(data, upstream='8.8.8.8'):
    """Forward a DNS query to an upstream server and return the response."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.sendto(data, (upstream, 53))
        resp, _ = s.recvfrom(512)
        s.close()
        return resp
    except Exception:
        return None


def _dns_server_loop(local_ip, domain):
    """Main loop of the mini DNS server."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', 53))
        sock.settimeout(1)
        while True:
            try:
                data, addr = sock.recvfrom(512)
                queried = _parse_dns_domain(data)
                if queried == domain.lower():
                    resp = _build_dns_response(data, local_ip)
                else:
                    resp = _forward_dns(data)
                if resp:
                    sock.sendto(resp, addr)
            except socket.timeout:
                continue
            except Exception:
                continue
    except Exception:
        pass


def start_dns_server(local_ip, domain=CUSTOM_DOMAIN):
    """Start the mini DNS server in a background daemon thread."""
    t = threading.Thread(target=_dns_server_loop, args=(local_ip, domain), daemon=True)
    t.start()
    return t


# ═══════════════════════════════════════════════════════════
# MAC ADDRESS SECURITY
# ═══════════════════════════════════════════════════════════

def get_all_mac_addresses():
    """Get all MAC addresses from the machine using system commands."""
    macs = set()
    try:
        # Method 1: uuid-based (primary adapter)
        mac_hex = uuid.getnode()
        mac_str = ':'.join(f'{(mac_hex >> i) & 0xFF:02X}' for i in range(40, -1, -8))
        macs.add(mac_str.replace(":", "-"))
    except Exception:
        pass

    try:
        # Method 2: getmac command for all adapters
        result = subprocess.run(
            ["getmac", "/fo", "csv", "/nh"],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in result.stdout.strip().split('\n'):
            parts = line.split(',')
            if parts:
                mac = parts[0].strip().strip('"')
                if len(mac) == 17 and '-' in mac:
                    macs.add(mac.upper())
    except Exception:
        pass

    return macs


def verify_mac_address():
    """Verify that the machine's MAC address is authorized."""
    machine_macs = get_all_mac_addresses()
    # By-pass MAC address restriction to allow any MAC address
    if machine_macs:
        return True, list(machine_macs)[0]
    return True, "UNKNOWN-MAC"


# ═══════════════════════════════════════════════════════════
# NEXUS SPLASH SCREEN
# ═══════════════════════════════════════════════════════════

def show_splash_screen(authorized_mac):
    """Show a NEXUS branded splash screen."""
    splash = tk.Tk()
    splash.title("NEXUS")
    splash.overrideredirect(True)
    splash.configure(bg="#0a0a1a")

    # Center on screen
    width, height = 600, 420
    screen_w = splash.winfo_screenwidth()
    screen_h = splash.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    splash.geometry(f"{width}x{height}+{x}+{y}")
    splash.attributes("-topmost", True)

    # Main frame with border effect
    outer_frame = tk.Frame(splash, bg="#00d4ff", padx=2, pady=2)
    outer_frame.pack(fill="both", expand=True)

    inner_frame = tk.Frame(outer_frame, bg="#0a0a1a")
    inner_frame.pack(fill="both", expand=True)

    # Top accent line
    accent = tk.Frame(inner_frame, bg="#00d4ff", height=3)
    accent.pack(fill="x", pady=(15, 0))

    # NEXUS Logo (ASCII Art)
    logo_text = """
 ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
 ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
 ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
 ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
 ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
 ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
"""

    logo_label = tk.Label(
        inner_frame,
        text=logo_text,
        font=("Consolas", 11, "bold"),
        fg="#00d4ff",
        bg="#0a0a1a",
        justify="center"
    )
    logo_label.pack(pady=(10, 5))

    # Subtitle
    subtitle = tk.Label(
        inner_frame,
        text="C O N T E N T   M A N A G E M E N T   S Y S T E M",
        font=("Segoe UI", 9, "bold"),
        fg="#4a9eff",
        bg="#0a0a1a"
    )
    subtitle.pack(pady=(0, 10))

    # Bottom accent line
    accent2 = tk.Frame(inner_frame, bg="#00d4ff", height=3)
    accent2.pack(fill="x")

    # Status info
    info_frame = tk.Frame(inner_frame, bg="#0a0a1a")
    info_frame.pack(pady=(15, 5))

    # Security badge
    security_label = tk.Label(
        info_frame,
        text=f"🔒  AUTHORIZED  │  MAC: {authorized_mac}",
        font=("Consolas", 9),
        fg="#00ff88",
        bg="#0a0a1a"
    )
    security_label.pack()

    # Network URL label - custom domain
    local_ip = get_local_ip()
    network_label = tk.Label(
        info_frame,
        text=f"DNS: http://{CUSTOM_DOMAIN}:8000",
        font=("Consolas", 9, "bold"),
        fg="#ffaa00",
        bg="#0a0a1a"
    )
    network_label.pack(pady=(3, 0))

    dns_hint = tk.Label(
        info_frame,
        text=f"(Set phone DNS to: {get_local_ip()})",
        font=("Consolas", 8),
        fg="#555555",
        bg="#0a0a1a"
    )
    dns_hint.pack()

    # Loading status
    status_var = tk.StringVar(value="⚡  Starting server...")
    status_label = tk.Label(
        inner_frame,
        textvariable=status_var,
        font=("Segoe UI", 10),
        fg="#888888",
        bg="#0a0a1a"
    )
    status_label.pack(pady=(15, 5))

    # Progress bar frame
    progress_frame = tk.Frame(inner_frame, bg="#1a1a2e", height=4)
    progress_frame.pack(fill="x", padx=40, pady=(5, 15))
    progress_frame.pack_propagate(False)

    progress_bar = tk.Frame(progress_frame, bg="#00d4ff", height=4, width=0)
    progress_bar.place(x=0, y=0, relheight=1)

    # Footer
    footer = tk.Label(
        inner_frame,
        text="© 2026 NEXUS Systems",
        font=("Segoe UI", 8),
        fg="#444444",
        bg="#0a0a1a"
    )
    footer.pack(side="bottom", pady=(0, 10))

    return splash, status_var, progress_bar, progress_frame


def animate_progress(splash, progress_bar, progress_frame, percentage):
    """Animate the progress bar to a given percentage."""
    try:
        total_width = progress_frame.winfo_width()
        target_width = int(total_width * percentage / 100)
        if target_width > 0:
            progress_bar.place_configure(width=target_width)
        splash.update()
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# SERVER MANAGEMENT
# ═══════════════════════════════════════════════════════════

def wait_for_server(host="localhost", port=8000, timeout=30):
    """Wait until the Django server is ready to accept connections."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def start_django_server():
    """Start the Django development server using the venv Python."""
    process = subprocess.Popen(
        [VENV_PYTHON, MANAGE_PY, "runserver", f"{SERVER_HOST}:{SERVER_PORT}"],
        cwd=BASE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    return process


# ═══════════════════════════════════════════════════════════
# BROWSER + F11 FULLSCREEN
# ═══════════════════════════════════════════════════════════

def send_f11():
    """Send F11 keypress to trigger fullscreen in the browser."""
    time.sleep(2)  # Wait for browser to be in focus

    # Use Windows API to send F11
    VK_F11 = 0x7A
    KEYEVENTF_KEYUP = 0x0002

    user32 = ctypes.windll.user32
    user32.keybd_event(VK_F11, 0, 0, 0)          # Key down
    time.sleep(0.05)
    user32.keybd_event(VK_F11, 0, KEYEVENTF_KEYUP, 0)  # Key up


def open_browser_fullscreen():
    """Open the browser and send F11 for fullscreen."""
    webbrowser.open(BROWSER_URL)
    # Send F11 in a separate thread to avoid blocking
    f11_thread = threading.Thread(target=send_f11, daemon=True)
    f11_thread.start()
    f11_thread.join(timeout=5)


# ═══════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════

def main():
    """Main launcher entry point."""

    # -- Step 1: Detect local IP, open Firewall & start DNS server --
    local_ip = get_local_ip()
    open_firewall_port()
    start_dns_server(local_ip, CUSTOM_DOMAIN)

    # ── Step 2: MAC Address Verification ──
    authorized, mac = verify_mac_address()
    if not authorized:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "NEXUS Security",
            "⛔ Access Denied!\n\n"
            "This device is not authorized to run NEXUS.\n"
            "Contact your administrator to register this device.\n\n"
            f"Device MACs: {', '.join(get_all_mac_addresses())}"
        )
        root.destroy()
        sys.exit(1)

    # ── Step 3: Show Splash Screen ──
    splash, status_var, progress_bar, progress_frame = show_splash_screen(mac)
    splash.update()
    time.sleep(0.5)

    # ── Step 4: Start Django Server ──
    animate_progress(splash, progress_bar, progress_frame, 20)
    status_var.set("⚡  Starting Django server...")
    splash.update()

    server_process = start_django_server()
    time.sleep(1)

    animate_progress(splash, progress_bar, progress_frame, 40)
    status_var.set("⏳  Waiting for server to be ready...")
    splash.update()

    # ── Step 4: Wait for server ──
    server_ready = wait_for_server(port=int(SERVER_PORT))

    if not server_ready:
        status_var.set("❌  Server failed to start!")
        splash.update()
        time.sleep(2)
        splash.destroy()
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "NEXUS Error",
            "Failed to start the Django server.\n"
            "Please check your configuration and try again."
        )
        root.destroy()
        sys.exit(1)

    animate_progress(splash, progress_bar, progress_frame, 70)
    status_var.set("✅  Server is running!")
    splash.update()
    time.sleep(0.5)

    # ── Step 5: Open browser ──
    animate_progress(splash, progress_bar, progress_frame, 90)
    status_var.set("🌐  Opening browser...")
    splash.update()
    time.sleep(0.5)

    animate_progress(splash, progress_bar, progress_frame, 100)
    status_var.set(f"🚀  NEXUS is ready!  │  LAN: http://{local_ip}:8000")
    splash.update()
    time.sleep(0.5)

    # Close splash
    splash.destroy()

    # Open browser using local IP (works for LAN too) and send F11
    webbrowser.open(f"http://{local_ip}:8000")
    f11_thread = threading.Thread(target=send_f11, daemon=True)
    f11_thread.start()
    f11_thread.join(timeout=5)


if __name__ == "__main__":
    main()
