# IPVanish Linux Client With GUI with WireGuard

A lightweight, open‑source **IPVanish VPN GUI client for Linux** written in Python 3, packaged as a portable x86_64 AppImage with seamless **WireGuard** integration and automatic connection. Works perfectly with latest modern Linux Distributions like Ubuntu, Debian, Pop OS, Zorin, etc.

> ⚠️ You need an active IPVanish subscription and valid credentials to use this client.

---

<p align="center">
  <img src="./icon.png" alt="IPVanish Linux Client Logo" width="140">
</p>

## Download

The easiest way to get started is with the prebuilt AppImage from the Releases page.

⬇️ [**Download latest AppImage**](https://github.com/ryanpaul01/IPVanish-Linux-Client/releases/latest/download/ipvanish-app-x86_64.AppImage)

![Visitors](https://api.visitorbadge.io/api/visitors?path=https%3A%2F%2Fgithub.com%2Fryanpaul01%2FIPVanish-Linux-Client&label=Downloads&labelColor=%23697689&countColor=%23f47373)

---
## Features

- ✅ Native **GUI client** for IPVanish on Linux (no CLI usage required)
- ✅ Written in **Python 3** for readability and easy contributions
- ✅ **AppImage** build for portable, single‑file deployment on most x86_64 distributions
- ✅ Integrated **WireGuard config download**: login → select server → click **Generate**
- ✅ Automatically connects using the downloaded WireGuard configuration file
- ✅ Displays **current country and IP address** at the top of the app window
- ✅ Convenient **Disconnect** button in the top‑right corner
- ✅ Uses NetworkManager / `nmcli` for reliable network control (where available)
- ✅ 100% open source and community‑driven

---

## Requirements

**Generally below tools comes by default is latest modern Linux Distributions like Ubuntu, Debian, Pop OS, Zorin, etc.** 

Before running the app, ensure the following components are available on your system:

- **Python 3.8+** (if running from source)
- **WireGuard** (kernel module and userland tools)
- **NetworkManager** with **`nmcli`**:
  - `nmcli` is typically installed by default on Ubuntu and many Debian‑based desktop systems that use NetworkManager.
  - On minimal/server installs you may need to install `network-manager`.

### Install WireGuard on Debian/Ubuntu

```bash
sudo apt update
sudo apt install wireguard
```

Some guides also recommend additional packages like `openresolv` depending on your use case.

### Install NetworkManager / nmcli (if missing)

If `nmcli` is not present (for example on minimal Debian/Ubuntu images):

```bash
sudo apt update
sudo apt install network-manager
```

After installing NetworkManager, you may need to restart the service or reboot for changes to fully apply.

---

## Quick Start

1. **Install prerequisites** (WireGuard and NetworkManager/nmcli) as shown above.
2. **Download** `ipvanish-app-x86_64.AppImage` from release.
3. **Make it executable:**
   ```bash
   chmod +x ipvanish-app-x86_64.AppImage
   ```
4. **Launch the app:**
  Just double click and open the file. Or you can open from terminal.
   ```bash
   ./ipvanish-app-x86_64.AppImage
   ```
5. In the **login window**, enter your IPVanish username and password.
6. After successful login, the main window opens and shows:
   - Your **current country and IP address** at the top of the app.
   - A **server list** where you can choose your desired IPVanish server.
   - A **Disconnect** button in the top‑right corner (when connected).
7. Select a server and click **Generate**:
   - The app downloads the corresponding **WireGuard configuration file** for that server.
   - It then **automatically connects** using that WireGuard configuration via WireGuard and NetworkManager.
8. When you want to stop the VPN connection, click the **Disconnect** button in the top‑right corner. It will also remove wireguard config from network manager.

---

## Run from Source (Python 3)

If you prefer to run the application directly from source instead of the AppImage:

### Clone and install

```bash
git clone git@gitlab.com:linux-app/ipvanish-linux-client.git
cd ipvanish-linux-client

# Optional: create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Launch the GUI

```bash
python3 ipvanish-app.py
```

This opens the same graphical interface as the AppImage build.

---

## Building the x86_64 AppImage

The repository includes a Bash script named `build-appimage.sh` to build the AppImage locally.

1. Ensure you have AppImage tooling installed (e.g. `appimagetool`) and any dependencies expected by `build-appimage.sh`.
2. From the project folder, run:

```bash
chmod +x build-appimage.sh
./build-appimage.sh
```

3. After a successful build, you should see the AppImage file named **ipvanish-app-x86_64.AppImage**

---

## How the App Works

The app is designed around a simple IPVanish + WireGuard flow:

1. **Start** the application (AppImage or `python3 ipvanish-app.py`).
2. **Log in** using your IPVanish account credentials.
3. The app shows your **current country and IP address** at the top, so you immediately see whether you are on your original IP or a VPN IP.
4. **Select a server** from the list in the main window.
5. Click **Generate**:
   - The app requests and downloads the **WireGuard config** for that server.
   - It then automatically **brings up the WireGuard connection** using the downloaded config.
6. While connected, the top bar continues to show updated **country/IP**, and the **Disconnect** button in the top‑right corner lets you quickly drop the VPN tunnel.
7. Click **Disconnect** to cleanly shut down the WireGuard connection.

---

## Configuration & Data

- The client may cache:
  - Your last selected server
  - Window layout or theme preferences
- The client should will store:
  - IPVanish cookie in plain text in ~/.config path
  - Private WireGuard configs in readable location ~/.config

---

## Roadmap

Potential future enhancements:

- System tray icon with quick connect/disconnect
- Kill‑switch and auto‑reconnect options

Suggestions and PRs are welcome.

---

## Contributing

1. **Fork** the repo.
2. Create a feature branch:
   ```bash
   git checkout -b feature/my-improvement
   ```
3. Implement your changes and add/update tests or docs where applicable.
4. Push and open a **Pull Request**.

Bug reports, feature requests, and small fixes are all appreciated.

---

## Security

- Never commit your own IPVanish credentials or any `.conf` WireGuard files to the repository.
- Treat WireGuard configuration files as **secret**; they contain keys that grant VPN access.
- If you discover a security issue, please report it privately to the maintainer instead of posting public exploit details.

---

## License

This project is released under the **MIT License**.

---

## Acknowledgements

- **IPVanish** name and logo are trademarks or registered trademarks of their respective owner and are used here solely to identify compatibility and integration with the IPVanish service. This project is an independent, community‑driven client and is not affiliated with, endorsed by, or officially supported by IPVanish.
- The **WireGuard** and **NetworkManager** communities for robust networking tools on Linux.
- Various public guides and discussions on nmcli and WireGuard on Debian/Ubuntu that helped shape the recommended install steps.
