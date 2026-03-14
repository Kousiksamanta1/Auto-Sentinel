# Auto-Sentinel

Auto-Sentinel is a Python MVC desktop application for WPA2 wireless security auditing with a modern PyQt6 GUI.

It supports three runtime modes:

- **macOS**: runs in **Mock Mode** with synthetic Wi-Fi data (for safe GUI testing).
- **Windows**: runs in **Mock Mode** with synthetic Wi-Fi data (for safe GUI testing).
- **Linux/Kali**: runs in **Hardware Mode** with `airmon-ng` and `airodump-ng` for passive scanning.

## Latest Updates (March 14, 2026)

- Fully implemented **Action Panel** with visible, high-contrast controls and improved spacing.
- Added **Wireless Interface** and **Monitor Mode State** dropdowns (`wlan0`, `wlan1`, `wlan0mon`; `Managed`, `Monitor`).
- Added **Operations** buttons: `Start Network Scan`, `Capture Handshake`, and `Parse Capture`.
- Added **Deauthentication Authorization** subsection with `Target BSSID`, `Deauth Packets (count)`, and `Authorize Deauthentication`.
- Connected all Action Panel operations to **QThread workers** to prevent GUI freezing.
- Wired button interactions into telemetry so events stream to the **Embedded Console** with timestamps and to `logs/auto_sentinel.log`.
- Kept **Mock Mode** fully functional for macOS/Windows by returning simulated success messages instead of hardware actions.
- Kept active deauthentication execution intentionally guarded/non-automated in hardware mode.

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
- Click `Start Network Scan` to stream fake access points in the table.

## 2) Run on Windows (Mock Mode) - Step by Step

Windows is detected as unsupported hardware mode, so Auto-Sentinel runs in safe Mock Mode.

### Step 1: Open PowerShell and go to project folder

```powershell
cd "C:\path\to\Auto-Sentinel"
```

### Step 2: Create and activate a virtual environment

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked, run this once in PowerShell:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```powershell
python -m pip install -U pip
python -m pip install -r requirements.txt
```

### Step 4: Start the app

```powershell
python main.py
```

### Step 5: Validate startup in GUI

- Environment chip should show `Windows` (or your detected platform).
- Runtime should indicate `Mock Mode`.
- Click `Start Network Scan` to stream fake access points in the table.

## 3) Run on Kali Linux (Hardware Mode) - Step by Step

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

1. Select interface (example: `wlan0`) from **Wireless Interface**.
2. Set **Monitor Mode State** to `Monitor` when needed.
3. Click **Start Network Scan**.
4. Watch live results in the dashboard.
5. Click **Parse Capture** for a summary.

## 4) Stop and Cleanup

- If scanning is active, click **Stop Network Scan** (same button toggles state) before closing when possible.
- Closing the app or pressing `Ctrl+C` triggers cleanup logic.
- Cleanup attempts to restore interface state back to Managed Mode.

If needed, manual recovery on Kali:

```bash
sudo airmon-ng stop wlan0mon
sudo ip link set wlan0 up
sudo iwconfig wlan0 mode managed
```

Adjust `wlan0` and `wlan0mon` to your actual interface names.

## 5) Logs and Output

- Runtime logs: `logs/auto_sentinel.log`
- Scan outputs (CSV): inside the `captures/scan_YYYYMMDD_HHMMSS/` folder

## 6) Troubleshooting

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

### PowerShell cannot run activation script

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## 7) Important Safety Notice

Use Auto-Sentinel only on networks and systems you own or are explicitly authorized to assess.

This build focuses on passive discovery and analysis workflows. Active deauthentication and automated handshake-capture actions are intentionally not implemented.
