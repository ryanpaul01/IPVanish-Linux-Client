#!/usr/bin/env python3
import os
import re
import json
import base64
import shutil
import subprocess
import threading
import urllib.request
import webview

TARGET_URL = "https://my.ipvanish.com/wireguard/"
API_URL = "https://api.my-ip.io/v2/ip.json"
APP_TITLE = "IPVanish WireGuard"
WINDOW_W = 1280
WINDOW_H = 820
DATA_DIR = os.path.join(os.path.expanduser("~"), ".config", "ipvanish-app")
VPN_CONF = os.path.join(DATA_DIR, "vpn.conf")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"

os.makedirs(DATA_DIR, exist_ok=True)
webview.settings["ALLOW_DOWNLOADS"] = True

TOPBAR_JS = r"""
(function() {
    function ensure() {
        if (document.getElementById('_tb_root')) return;

        var root = document.createElement('div');
        root.id = '_tb_root';
        root.style.cssText = [
            'position:fixed','top:0','left:0','right:0','height:48px',
            'background:#111827','color:#fff','z-index:2147483647',
            'display:flex','align-items:center','justify-content:space-between',
            'padding:0 12px','box-sizing:border-box','font-family:sans-serif',
            'box-shadow:0 2px 10px rgba(0,0,0,.45)'
        ].join(';');

        var left = document.createElement('div');
        var center = document.createElement('div');
        var right = document.createElement('div');

        left.style.cssText = 'width:120px;display:flex;justify-content:flex-start;';
        center.style.cssText = 'flex:1;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px;color:#d1d5db;letter-spacing:.3px;';
        right.style.cssText = 'width:120px;display:flex;justify-content:flex-end;';

        var back = document.createElement('button');
        back.textContent = 'Back';
        back.style.cssText = 'background:#374151;color:#fff;border:none;border-radius:6px;padding:7px 12px;cursor:pointer;';
        back.onclick = function(){ window.history.back(); };

        var disconnect = document.createElement('button');
        disconnect.textContent = 'Disconnect';
        disconnect.id = '_tb_disconnect';
        disconnect.style.cssText = 'background:#dc2626;color:#fff;border:none;border-radius:6px;padding:7px 12px;cursor:pointer;font-weight:600;';
        disconnect.onclick = function(){ window.pywebview.api.disconnect_vpn(); };

        left.appendChild(back);
        right.appendChild(disconnect);
        root.appendChild(left);
        root.appendChild(center);
        root.appendChild(right);

        document.body.insertBefore(root, document.body.firstChild);

        var pad = document.createElement('div');
        pad.id = '_tb_pad';
        pad.style.cssText = 'height:48px;';
        document.body.insertBefore(pad, root.nextSibling);
    }

    window.refreshIp = function() {
        var center = document.querySelector('#_tb_root > div:nth-child(2)');
        if (!center) return;
        center.textContent = 'Refreshing...';
        fetch('""" + API_URL + """?nocache=' + Date.now())
            .then(r => r.json())
            .then(d => {
                center.textContent = (d.country.name || 'Unknown') + ' | ' + (d.ip || 'Unknown');
            })
            .catch(() => {
                center.textContent = 'IP unavailable';
            });
    };

    function hookDownloads() {
        if (window._download_hooked) return;
        window._download_hooked = true;

        document.addEventListener('click', function(e) {
            var a = e.target.closest('a');
            if (!a) return;
            if (a.closest && a.closest('#_tb_root')) return;

            var href = a.getAttribute('href') || '';
            var dl = a.getAttribute('download');

            if (href.startsWith('blob:')) {
                e.preventDefault();
                fetch(href).then(r => r.arrayBuffer()).then(buf => {
                    var bytes = new Uint8Array(buf);
                    var bin = '';
                    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
                    window.pywebview.api.save_b64(btoa(bin), 'vpn.conf');
                });
                return;
            }

            if (dl !== null || href.toLowerCase().endsWith('.bin')) {
                e.preventDefault();
                window.pywebview.api.download_url(a.href, 'vpn.conf');
            }
        }, true);
    }

    function inject() {
        ensure();
        window.refreshIp();
        hookDownloads();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', inject);
    } else {
        inject();
    }
})();
"""

OVERLAY_JS = lambda msg: "(function(){var e=document.getElementById('_ov');if(!e){e=document.createElement('div');e.id='_ov';e.style.cssText='position:fixed;bottom:18px;right:18px;z-index:2147483647;background:rgba(17,24,39,.95);color:#fff;padding:10px 14px;border-radius:8px;font:13px monospace;box-shadow:0 6px 24px rgba(0,0,0,.45);transition:opacity .25s;min-width:220px;';document.body.appendChild(e);}e.textContent=" + json.dumps(msg) + ";e.style.opacity='1';})();"
HIDE_OVERLAY_JS = "(function(){var e=document.getElementById('_ov');if(e){e.style.opacity='0';setTimeout(function(){if(e&&e.parentNode)e.parentNode.removeChild(e);},250);}})();"
REFRESH_IP_JS = "if(typeof window.refreshIp==='function') window.refreshIp();"

def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def nm_all_wireguard_connections():
    """Return list of (name, uuid) for ALL WireGuard connections in NetworkManager, active or not."""
    p = run_cmd(["nmcli", "-t", "-f", "UUID,NAME,TYPE", "connection", "show"])
    results = []
    if p.returncode == 0:
        for line in p.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[2] == "wireguard":
                results.append((parts[1], parts[0]))  # (name, uuid)
    return results

def nm_active_wireguard_connections():
    """Return list of (name, uuid) for currently ACTIVE WireGuard connections."""
    p = run_cmd(["nmcli", "-t", "-f", "UUID,NAME,TYPE", "connection", "show", "--active"])
    results = []
    if p.returncode == 0:
        for line in p.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[2] == "wireguard":
                results.append((parts[1], parts[0]))  # (name, uuid)
    return results

class NmVpn:
    def __init__(self):
        self.connection_name = None
        self.uuid = None

    def import_and_up(self, conf_path):
        """Import a .conf file into NetworkManager and bring it up."""
        self.stop_own()
        if not shutil.which("nmcli"):
            raise RuntimeError("nmcli not found. Install network-manager.")

        p = subprocess.run(
            ["nmcli", "connection", "import", "type", "wireguard", "file", conf_path],
            capture_output=True, text=True
        )
        if p.returncode != 0:
            raise RuntimeError((p.stderr or p.stdout or "nmcli import failed").strip())

        out = (p.stdout or "").strip()
        m = re.search(r"Connection '(.+?)' \((.+?)\) successfully added", out)
        if m:
            self.connection_name = m.group(1)
            self.uuid = m.group(2)
        else:
            m2 = re.search(r"Connection '(.+?)' successfully added", out)
            if m2:
                self.connection_name = m2.group(1)

        if not self.connection_name:
            raise RuntimeError("Could not determine imported connection name from: " + out)

        p3 = subprocess.run(
            ["nmcli", "connection", "up", self.connection_name],
            capture_output=True, text=True
        )
        if p3.returncode != 0:
            raise RuntimeError((p3.stderr or p3.stdout or "nmcli up failed").strip())

    def stop_own(self):
        """Disconnect and delete the connection this app imported."""
        if self.connection_name:
            run_cmd(["nmcli", "connection", "down", self.connection_name])
            run_cmd(["nmcli", "connection", "delete", self.connection_name])
        elif self.uuid:
            run_cmd(["nmcli", "connection", "down", "uuid", self.uuid])
            run_cmd(["nmcli", "connection", "delete", "uuid", self.uuid])
        self.connection_name = None
        self.uuid = None

    def stop_all_wireguard(self):
        """Disconnect and delete ALL WireGuard connections regardless of who created them."""
        for name, uuid in nm_all_wireguard_connections():
            run_cmd(["nmcli", "connection", "down", name])
            run_cmd(["nmcli", "connection", "delete", "uuid", uuid])
        self.connection_name = None
        self.uuid = None

vpn = NmVpn()

class Api:
    def __init__(self):
        self.window = None

    def set_window(self, window):
        self.window = window

    def _show(self, msg):
        if self.window:
            self.window.evaluate_js(OVERLAY_JS(msg))

    def _hide(self):
        if self.window:
            self.window.evaluate_js(HIDE_OVERLAY_JS)

    def _refresh_ip(self):
        import time
        time.sleep(2)  # brief pause so new IP is assigned before refresh
        if self.window:
            self.window.evaluate_js(REFRESH_IP_JS)

    def save_b64(self, b64_data, _name):
        threading.Thread(target=self._save_and_start, args=(b64_data,), daemon=True).start()

    def download_url(self, url, _name):
        threading.Thread(target=self._fetch_and_start, args=(url,), daemon=True).start()

    def _save_and_start(self, b64_data):
        try:
            self._show("Saving vpn.conf...")
            raw = base64.b64decode(b64_data + "==")
            with open(VPN_CONF, "wb") as f:
                f.write(raw)
            self._show("Saved. Importing into NetworkManager...")
            vpn.import_and_up(VPN_CONF)
            self._show("VPN connected")
            threading.Thread(target=self._refresh_ip, daemon=True).start()
        except Exception as e:
            self._show("Error: " + str(e))
        finally:
            self._hide()

    def _fetch_and_start(self, url):
        try:
            self._show("Downloading vpn.conf...")
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(VPN_CONF, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            self._show("Saved. Importing into NetworkManager...")
            vpn.import_and_up(VPN_CONF)
            self._show("VPN connected")
            threading.Thread(target=self._refresh_ip, daemon=True).start()
        except Exception as e:
            self._show("Error: " + str(e))
        finally:
            self._hide()

    def disconnect_vpn(self):
        """
        Disconnect ALL WireGuard connections (not just ones this app made).
        Then clear local config and refresh IP.
        """
        threading.Thread(target=self._do_disconnect, daemon=True).start()

    def _do_disconnect(self):
        try:
            active = nm_active_wireguard_connections()
            if not active:
                self._show("No active WireGuard VPN found")
            else:
                self._show("Disconnecting " + str(len(active)) + " WireGuard connection(s)...")
                vpn.stop_all_wireguard()
                self._show("All WireGuard VPNs disconnected")
            if os.path.exists(VPN_CONF):
                os.remove(VPN_CONF)
            threading.Thread(target=self._refresh_ip, daemon=True).start()
        except Exception as e:
            self._show("Disconnect error: " + str(e))
        finally:
            self._hide()

def main():
    api = Api()
    window = webview.create_window(
        APP_TITLE,
        TARGET_URL,
        width=WINDOW_W,
        height=WINDOW_H,
        resizable=True,
        js_api=api,
    )
    api.set_window(window)
    window.events.loaded += lambda: window.evaluate_js(TOPBAR_JS)
    webview.start(
        gui="qt",
        user_agent=USER_AGENT,
        private_mode=False,
        storage_path=DATA_DIR,
        debug=False,
    )

if __name__ == "__main__":
    main()
