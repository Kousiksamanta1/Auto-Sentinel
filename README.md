# Auto-Sentinel

Auto-Sentinel is a Python MVC desktop application for WPA2 wireless security auditing with a modern PyQt6 GUI.

It supports two runtime modes:

- **macOS**: runs in **Mock Mode** with synthetic Wi-Fi data (for safe GUI testing).
- **Linux/Kali**: runs in **Hardware Mode** with `airmon-ng` and `airodump-ng` for passive scanning.

## Tech Stack

- Python 3.10+
- PyQt6
- pandas

## Project Layout

```text
Auto-Sentinel/
├── main.py
├── requirements.txt
├── core/
│   ├── logic.py
│   ├── controller.py
│   ├── models.py
│   ├── parsers.py
│   ├── environment.py
│   └── logging_config.py
└── ui/
    ├── main_window.py
    ├── workers.py
    └── styles.py
```

## 1) Run on macOS (Mock Mode) - Step by Step

macOS is automatically detected and uses synthetic Wi-Fi scan data.

### Step 1: Open Terminal and go to project folder

```bash
cd "/path/to/Auto-Sentinel"
```

### Step 2: Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install dependencies

```bash
python -m pip install -U pip
python -m pip install -r requirements.txt
```

### Step 4: Start the app

```bash
python main.py
```

### Step 5: Validate startup in GUI

- Environment chip should show `macOS`.
- Runtime should indicate `Mock Mode`.
- `Target Scan` will show fake access points in the table.

## 2) Run on Kali Linux (Hardware Mode) - Step by Step

Kali/Linux mode uses real wireless tools and interface operations.

### Step 1: Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip aircrack-ng wireless-tools net-tools
```

### Step 2: Open project folder

```bash
cd "/path/to/Auto-Sentinel"
```

### Step 3: Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 4: Install Python dependencies

```bash
python -m pip install -U pip
python -m pip install -r requirements.txt
```

### Step 5: Verify wireless CLI tools are available

```bash
command -v airmon-ng
command -v airodump-ng
command -v aireplay-ng
```

### Step 6: Find your wireless interface

```bash
ip link
```

Use names like `wlan0` in the GUI.

### Step 7: Start the app

Hardware mode usually needs elevated privileges for monitor operations:

```bash
sudo .venv/bin/python main.py
```

### Step 8: Run a passive scan from the GUI

1. Enter interface (example: `wlan0`).
2. Click **Start Monitor Mode**.
3. Click **Target Scan**.
4. Watch live results in the dashboard.
5. Click **Analyze Results** for a summary.

## 3) Stop and Cleanup

- Click **Stop Target Scan** before closing when possible.
- Closing the app or pressing `Ctrl+C` triggers cleanup logic.
- Cleanup attempts to restore interface state back to Managed Mode.

If needed, manual recovery on Kali:

```bash
sudo airmon-ng stop wlan0mon
sudo ip link set wlan0 up
sudo iwconfig wlan0 mode managed
```

Adjust `wlan0` and `wlan0mon` to your actual interface names.

## 4) Logs and Output

- Runtime logs: `logs/auto_sentinel.log`
- Scan outputs (CSV): inside the `captures/scan_YYYYMMDD_HHMMSS/` folder

## 5) Troubleshooting

### `ModuleNotFoundError: No module named 'PyQt6'`

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### `airmon-ng not found`

```bash
sudo apt install -y aircrack-ng
```

### Permission denied while enabling monitor mode

Run with elevated privileges:

```bash
sudo .venv/bin/python main.py
```

### Empty scan table in Kali

- Ensure adapter supports monitor mode.
- Confirm interface name is correct.
- Ensure monitor mode was started successfully in console output.

## 6) Important Safety Notice

Use Auto-Sentinel only on networks and systems you own or are explicitly authorized to assess.

This build focuses on passive discovery and analysis workflows. Active deauthentication and automated handshake-capture actions are intentionally not implemented.
