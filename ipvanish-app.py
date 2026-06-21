#!/usr/bin/env python3
import base64
import json
import os
import sys
import re
import shutil
import subprocess
import threading
import urllib.request



import webview

TARGET_URL = "https://my.ipvanish.com/wireguard/"
API_URL = "https://www.whatismyip.net/geoip/"
APP_TITLE = "IPVanish VPN"
WINDOW_W = 1280
WINDOW_H = 820
DATA_DIR = os.path.join(os.path.expanduser("~"), ".config", "ipvanish-app")
VPN_CONF = os.path.join(DATA_DIR, "vpn.conf")
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"
APP_VERSION = "2.0"
GITHUB_OWNER = "ryanpaul01"
GITHUB_REPO = "IPVanish-Linux-Client"
GITHUB_LATEST_API = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)

os.makedirs(DATA_DIR, exist_ok=True)
webview.settings["ALLOW_DOWNLOADS"] = True

TERMINAL_CANDIDATES = [
    ["gnome-terminal", "--"],
    ["konsole", "--new-tab", "-e"],
    ["xfce4-terminal", "-e"],
    ["xterm", "-e"],
    ["mate-terminal", "-e"],
    ["lxterminal", "-e"],
    ["xdg-terminal-exec"],
]


def _launch_terminal_for_password(script_path):
    """Open a terminal window that runs a one-off sudoers setup for nft.
    The user enters their sudo password in that terminal; no password flows through this app.
    """
    sudoers_line = f"{_current_username()} ALL=(ALL) NOPASSWD: /usr/sbin/nft"
    setup_cmd = (
        f"echo '{sudoers_line}' | sudo tee {SUDOERS_FILE}; "
        f"sudo chmod 440 {SUDOERS_FILE}; "
        f"sudo visudo -c -f {SUDOERS_FILE}; "
        "echo; echo 'Kill switch sudoers setup finished. You can close this window.'; "
        "read -r -p 'Press Enter to close...' _"
    )
    cmdline = None
    for base in TERMINAL_CANDIDATES:
        exe = base[0]
        if shutil.which(exe):
            if exe == "gnome-terminal":
                cmdline = [exe, "--", "bash", "-lc", setup_cmd]
            else:
                cmdline = [exe] + base[1:] + ["bash", "-lc", setup_cmd]
            break
    if cmdline is None:
        return False
    subprocess.Popen(cmdline)
    return True


SUDOERS_FILE = "/etc/sudoers.d/ipvanish-nft"


def _nft(*args, stdin_data=None):
    return subprocess.run(["sudo", "-n", "/usr/sbin/nft"] + list(args), capture_output=True, text=True, check=False, input=stdin_data)


def _nft_sudoers_ok():
    return _nft("--version").returncode == 0


def killswitch_enable():
    _nft("delete", "table", "ip6", "ipvanish_killswitch")
    result = _nft("-f", "-", stdin_data=NFT_RULESET)
    if result.returncode != 0:
        raise RuntimeError("nft kill-switch enable failed: " + (result.stderr or result.stdout).strip())


def killswitch_disable():
    _nft("delete", "table", "ip6", "ipvanish_killswitch")


def killswitch_is_active():
    return _nft("list", "table", "ip6", "ipvanish_killswitch").returncode == 0

NFT_RULESET = """table ip6 ipvanish_killswitch {
    chain input {
        type filter hook input priority -100; policy drop;
        ct state established,related accept
        iifname \"lo\" accept
    }
    chain forward {
        type filter hook forward priority -100; policy drop;
    }
    chain output {
        type filter hook output priority -100; policy drop;
        oifname \"lo\" accept
        ct state established,related accept
    }
}
"""


def _current_username():
    import pwd

    return pwd.getpwuid(os.getuid()).pw_name


def _nft(*args, stdin_data=None):
    return subprocess.run(
        ["sudo", "-n", "/usr/sbin/nft"] + list(args),
        capture_output=True,
        text=True,
        check=False,
        input=stdin_data,
    )


def _nft_sudoers_ok():
    return _nft("--version").returncode == 0





TOPBAR_JS = (
    r"""
(function() {
  function ensure() {
    if (document.getElementById('_tb_root')) return;
    var root = document.createElement('div');
    root.id = '_tb_root';
    root.style.cssText = ['position:fixed','top:0','left:0','right:0','height:48px','background:#111827','color:#fff','z-index:2147483647','display:flex','align-items:center','justify-content:space-between','padding:0 12px','box-sizing:border-box','font-family:sans-serif','box-shadow:0 2px 10px rgba(0,0,0,.45)'].join(';');
    var left = document.createElement('div');
    var center = document.createElement('div');
    var right = document.createElement('div');
    left.style.cssText = 'width:120px;display:flex;justify-content:flex-start;';
    center.style.cssText = 'flex:1;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:13px;color:#d1d5db;letter-spacing:.3px;';
    right.style.cssText = 'width:120px;display:flex;justify-content:flex-end;';
    var back = document.createElement('button');
    back.textContent = 'Back';
    back.style.cssText = 'background:#374151;color:#fff;border:none;border-radius:6px;padding:7px 12px;cursor:pointer;';
    back.onclick = function() { window.history.back(); };
    var version = document.createElement('div');
    version.textContent = 'Version: """+ APP_VERSION + """';
    version.style.cssText = 'margin-left:10px;font-size:12px;color:#9ca3af;white-space:nowrap;';
    var disconnect = document.createElement('button');
    disconnect.textContent = 'Disconnect';
    disconnect.style.cssText = 'background:#dc2626;color:#fff;border:none;border-radius:6px;padding:7px 12px;cursor:pointer;font-weight:600;';
    disconnect.onclick = function() { window.pywebview.api.disconnect_vpn(); };
    left.appendChild(back);
    left.appendChild(version);
    right.appendChild(disconnect);
    root.appendChild(left);
    root.appendChild(center);
    root.appendChild(right);
    document.body.insertBefore(root, document.body.firstChild);
    var pad = document.createElement('div');
    pad.style.cssText = 'height:48px;';
    document.body.insertBefore(pad, root.nextSibling);
    window.refreshIp = function() {
      var c = document.querySelector('#_tb_root > div:nth-child(2)');
      if (!c) return;
      c.textContent = 'Refreshing...';
      fetch('"""
    + API_URL
    + """?nocache=' + Date.now())
        .then(function(r) { return r.json(); })
        .then(function(d) {
          var ip = d.ip || d.query || 'Unknown';
          var city = d.city || '';
          var country = d.country || d.country_name || '';
          var location = '';
          if (city && country) location = city + ', ' + country;
          else if (country) location = country;
          else if (city) location = city;
          c.textContent = ip + (location ? ' | ' + location : '');
        })
        .catch(function() { c.textContent = 'IP unavailable'; });
    };
    function hookDownloads() {
      if (window._download_hooked) return;
      window._download_hooked = true;
      document.addEventListener('click', function(e) {
        var a = e.target.closest('a');
        if (!a) return;
        if (a.closest('#_tb_root')) return;
        var href = a.getAttribute('href') || '';
        var dl = a.getAttribute('download');
        if (href.indexOf('blob:') === 0) {
          e.preventDefault();
          fetch(href).then(function(r) { return r.arrayBuffer(); }).then(function(buf) {
            var bytes = new Uint8Array(buf);
            var bin = '';
            for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
            window.pywebview.api.save_b64(btoa(bin), 'vpn.conf');
          });
          return;
        }
        if (dl !== null || href.toLowerCase().indexOf('.bin') !== -1) {
          e.preventDefault();
          window.pywebview.api.download_url(a.href, 'vpn.conf');
        }
      }, true);
    }
    window.refreshIp();
    hookDownloads();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function() { ensure(); });
  else ensure();
})();
"""
)

OVERLAY_JS = lambda msg: (
    "(function(){var e=document.getElementById('_ov');if(!e){e=document.createElement('div');e.id='_ov';e.style.cssText='position:fixed;bottom:18px;right:18px;z-index:2147483647;background:rgba(17,24,39,.95);color:#fff;padding:10px 14px;border-radius:8px;font:13px monospace;box-shadow:0 6px 24px rgba(0,0,0,.45);transition:opacity .25s;min-width:220px;';document.body.appendChild(e);}e.textContent="
    + json.dumps(msg)
    + ";e.style.opacity='1';})();"
)
HIDE_OVERLAY_JS = "(function(){var e=document.getElementById('_ov');if(e){e.style.opacity='0';setTimeout(function(){if(e&&e.parentNode)e.parentNode.removeChild(e);},250);}})();"
REFRESH_IP_JS = "if(typeof window.refreshIp==='function') window.refreshIp();"
UPDATE_OVERLAY_JS = lambda msg: (
    "(function(){"
    "var e=document.getElementById('_upd');"
    "if(!e){"
    "e=document.createElement('div');e.id='_upd';"
    "e.style.cssText='position:fixed;top:58px;right:18px;z-index:2147483647;background:#0f172a;color:#fff;padding:12px 14px;border-radius:10px;font:13px sans-serif;box-shadow:0 8px 28px rgba(0,0,0,.35);max-width:340px;';"
    "document.body.appendChild(e);}"
    "e.innerHTML=" + json.dumps(msg) + ";"
    "})();"
)


def nm_all_wireguard_connections():
    p = subprocess.run(
        ["nmcli", "-t", "-f", "UUID,NAME,TYPE", "connection", "show"],
        capture_output=True,
        text=True,
        check=False,
    )
    results = []
    if p.returncode == 0:
        for line in p.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[2] == "wireguard":
                results.append((parts[1], parts[0]))
    return results


def nm_active_wireguard_connections():
    p = subprocess.run(
        ["nmcli", "-t", "-f", "UUID,NAME,TYPE", "connection", "show", "--active"],
        capture_output=True,
        text=True,
        check=False,
    )
    results = []
    if p.returncode == 0:
        for line in p.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[2] == "wireguard":
                results.append((parts[1], parts[0]))
    return results


class NmVpn:
    def __init__(self):
        self.connection_name = None
        self.uuid = None

    def import_and_up(self, conf_path):
        self.stop_own()
        if not shutil.which("nmcli"):
            raise RuntimeError("nmcli not found. Install network-manager.")
        p = subprocess.run(
            ["nmcli", "connection", "import", "type", "wireguard", "file", conf_path],
            capture_output=True,
            text=True,
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
            raise RuntimeError(
                "Could not determine imported connection name from: " + out
            )
        p3 = subprocess.run(
            ["nmcli", "connection", "up", self.connection_name],
            capture_output=True,
            text=True,
        )
        if p3.returncode != 0:
            raise RuntimeError((p3.stderr or p3.stdout or "nmcli up failed").strip())

    def stop_own(self):
        if self.connection_name:
            subprocess.run(
                ["nmcli", "connection", "down", self.connection_name],
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["nmcli", "connection", "delete", self.connection_name],
                capture_output=True,
                text=True,
                check=False,
            )
        elif self.uuid:
            subprocess.run(
                ["nmcli", "connection", "down", "uuid", self.uuid],
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["nmcli", "connection", "delete", "uuid", self.uuid],
                capture_output=True,
                text=True,
                check=False,
            )
        self.connection_name = None
        self.uuid = None

    def stop_all_wireguard(self):
        for name, uuid in nm_all_wireguard_connections():
            subprocess.run(
                ["nmcli", "connection", "down", name],
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["nmcli", "connection", "delete", "uuid", uuid],
                capture_output=True,
                text=True,
                check=False,
            )
        self.connection_name = None
        self.uuid = None


vpn = NmVpn()


def check_github_update(window=None):
    try:
        req = urllib.request.Request(
            GITHUB_LATEST_API,
            headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        latest = str(data.get("tag_name", "")).strip()
        html_url = (
            str(data.get("html_url", "")).strip()
            or f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
        )
        if latest and latest != APP_VERSION:
            msg = f'Update available: <a href="{html_url}" target="_blank" style="color:#93c5fd;text-decoration:underline;"><b>{latest}</b></a>'
            if window:
                window.evaluate_js(UPDATE_OVERLAY_JS(msg))
            return True, latest, html_url
    except Exception:
        pass
    return False, None, None


class Api:
    def __init__(self):
        self.window = None
        self.password = None
        self.password_event = threading.Event()
        self.prompt_mode = False

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

        time.sleep(2)
        if self.window:
            self.window.evaluate_js(REFRESH_IP_JS)

    def submit_password(self, password):
        self.password = password
        self.password_event.set()
        return True

    def save_b64(self, b64_data, _name):
        threading.Thread(
            target=self._save_and_start, args=(b64_data,), daemon=True
        ).start()

    def download_url(self, url, _name):
        threading.Thread(target=self._fetch_and_start, args=(url,), daemon=True).start()

    def _ensure_sudoers_gui(self):
        if _nft_sudoers_ok():
            return True
        script_path = os.path.abspath(__file__)
        self._show("Opening terminal to configure IPv6 kill switch sudoers. Enter your sudo password there.")
        ok = _launch_terminal_for_password(script_path)
        if not ok:
            self._show("No terminal emulator found; cannot configure kill switch sudoers.")
            return False
        import time
        for _ in range(300):
            if _nft_sudoers_ok():
                self._show("IPv6 kill switch sudoers configured successfully.")
                return True
            time.sleep(1)
        self._show("Timed out waiting for sudoers configuration. Kill switch may not be active.")
        return False

    def _save_and_start(self, b64_data):
        try:
            self._show("Saving Wireguard file...")
            raw = base64.b64decode(b64_data + "==")
            with open(VPN_CONF, "wb") as f:
                f.write(raw)
            self._ensure_sudoers_gui()
            self._show("Enabling IPv6 kill switch...")
            killswitch_enable()
            self._show("IPv6 kill switch active")
            vpn.import_and_up(VPN_CONF)
            self._show("VPN connected")
            threading.Thread(target=self._refresh_ip, daemon=True).start()
        except Exception as e:
            killswitch_disable()
            self._show("Error: " + str(e))
        finally:
            self._hide()

    def _fetch_and_start(self, url):
        try:
            self._show("Downloading Wireguard conf...")
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as resp:
                with open(VPN_CONF, "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
            self._ensure_sudoers_gui()
            self._show("Enabling IPv6 kill switch...")
            killswitch_enable()
            self._show("IPv6 kill switch active")
            vpn.import_and_up(VPN_CONF)
            self._show("VPN connected")
            threading.Thread(target=self._refresh_ip, daemon=True).start()
        except Exception as e:
            killswitch_disable()
            self._show("Error: " + str(e))
        finally:
            self._hide()

    def disconnect_vpn(self):
        threading.Thread(target=self._do_disconnect, daemon=True).start()

    def _do_disconnect(self):
        try:
            active = nm_active_wireguard_connections()
            if not active:
                self._show("No active WireGuard VPN found")
            else:
                self._show(
                    "Disconnecting " + str(len(active)) + " WireGuard connection(s)..."
                )
                vpn.stop_all_wireguard()
                self._show("All WireGuard VPNs disconnected")
            killswitch_disable()
            self._show("IPv6 kill switch removed")
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

    def on_loaded():
        window.evaluate_js(TOPBAR_JS)
        threading.Thread(
            target=check_github_update, args=(window,), daemon=True
        ).start()

    window.events.loaded += on_loaded
    webview.start(
        gui="qt",
        user_agent=USER_AGENT,
        private_mode=False,
        storage_path=DATA_DIR,
        debug=False,
    )


if __name__ == "__main__":
    if "--terminal-password" in os.sys.argv:
        terminal_password_mode()
    else:
        main()
