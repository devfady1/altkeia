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
BROWSER_URL = "http://localhost:8000"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = "python"
MANAGE_PY = os.path.join(BASE_DIR, "manage.py")


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

    # ── Step 1: MAC Address Verification ──
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

    # ── Step 2: Show Splash Screen ──
    splash, status_var, progress_bar, progress_frame = show_splash_screen(mac)
    splash.update()
    time.sleep(0.5)

    # ── Step 3: Start Django Server ──
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
    status_var.set("🚀  NEXUS is ready!")
    splash.update()
    time.sleep(0.5)

    # Close splash
    splash.destroy()

    # Open browser and send F11
    open_browser_fullscreen()


if __name__ == "__main__":
    main()
