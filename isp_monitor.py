#!/usr/bin/env python3
"""
ISP-Monitor — Dual ISP Uptime & Latency Monitor
Author: Srinivasan S (SRINIVASAN55)

Monitors two ISP connections simultaneously:
  - Pings each ISP gateway/DNS at regular intervals
  - Measures latency and packet loss
  - Sends email alerts to IT team on:
      • ISP down (no response)
      • Latency spike above threshold
      • ISP recovery (back online)
  - Logs all events to file + console
  - Auto-failover detection
"""

import os
import re
import sys
import time
import json
import socket
import struct
import select
import smtplib
import logging
import argparse
import platform
import subprocess
import threading
from datetime import datetime
from collections import deque
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict

# ─── Colors ───────────────────────────────────────────────────────────────────
class C:
    RED="\033[91m"; GREEN="\033[92m"; YELLOW="\033[93m"
    CYAN="\033[96m"; BOLD="\033[1m"; RESET="\033[0m"

BANNER = f"""{C.CYAN}{C.BOLD}
  ██╗███████╗██████╗       ███╗   ███╗ ██████╗ ███╗   ██╗██╗████████╗ ██████╗ ██████╗
  ██║██╔════╝██╔══██╗      ████╗ ████║██╔═══██╗████╗  ██║██║╚══██╔══╝██╔═══██╗██╔══██╗
  ██║███████╗██████╔╝█████╗██╔████╔██║██║   ██║██╔██╗ ██║██║   ██║   ██║   ██║██████╔╝
  ██║╚════██║██╔═══╝ ╚════╝██║╚██╔╝██║██║   ██║██║╚██╗██║██║   ██║   ██║   ██║██╔══██╗
  ██║███████║██║           ██║ ╚═╝ ██║╚██████╔╝██║ ╚████║██║   ██║   ╚██████╔╝██║  ██║
  ╚═╝╚══════╝╚═╝           ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
                    Dual ISP Uptime & Latency Monitor v1.0  |  Author: SRINIVASAN55
{C.RESET}"""

# ─── Config ────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "isps": [
        {
            "name": "ISP-1 (Primary)",
            "gateway": "8.8.8.8",
            "backup_hosts": ["8.8.4.4", "1.1.1.1"],
            "description": "Primary broadband link"
        },
        {
            "name": "ISP-2 (Backup)",
            "gateway": "1.1.1.1",
            "backup_hosts": ["1.0.0.1", "9.9.9.9"],
            "description": "Secondary/failover link"
        }
    ],
    "thresholds": {
        "latency_warn_ms": 100,
        "latency_critical_ms": 300,
        "packet_loss_warn_pct": 10,
        "packet_loss_critical_pct": 30,
        "consecutive_failures": 3,
        "check_interval_sec": 30,
        "ping_count": 5,
        "ping_timeout_sec": 3
    },
    "email": {
        "enabled": False,
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "sender": "isp.monitor@yourdomain.com",
        "password": "YOUR_APP_PASSWORD",
        "recipients": ["it-team@yourdomain.com", "noc@yourdomain.com"],
        "alert_cooldown_min": 15
    },
    "logging": {
        "log_file": "isp_monitor.log",
        "json_log": "isp_events.json",
        "history_points": 100
    }
}

# ─── Data Models ───────────────────────────────────────────────────────────────
@dataclass
class PingResult:
    host: str
    success: bool
    latency_ms: float = 0.0
    packet_loss_pct: float = 100.0
    error: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

@dataclass
class ISPStatus:
    name: str
    gateway: str
    state: str = "UNKNOWN"        # UP / DOWN / DEGRADED / UNKNOWN
    latency_ms: float = 0.0
    packet_loss_pct: float = 0.0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_up: Optional[str] = None
    last_down: Optional[str] = None
    last_alert_time: float = 0.0
    downtime_start: Optional[float] = None
    history: deque = field(default_factory=lambda: deque(maxlen=100))
    alert_sent: bool = False

    @property
    def uptime_str(self) -> str:
        if self.downtime_start:
            secs = int(time.time() - self.downtime_start)
            return f"DOWN {secs//3600:02d}h:{(secs%3600)//60:02d}m:{secs%60:02d}s"
        return "UP"

@dataclass
class Alert:
    isp_name: str
    level: str          # CRITICAL / WARNING / RECOVERY / INFO
    subject: str
    body: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─── Pinger ────────────────────────────────────────────────────────────────────
class Pinger:
    """Cross-platform pinger using system ping command."""

    @staticmethod
    def ping(host: str, count: int = 5, timeout: int = 3) -> PingResult:
        os_name = platform.system().lower()
        if os_name == "windows":
            cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
        else:
            cmd = ["ping", "-c", str(count), "-W", str(timeout), "-q", host]

        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * count + 5)
            stdout = out.stdout + out.stderr

            # Parse packet loss
            loss = 100.0
            loss_match = re.search(r'(\d+(?:\.\d+)?)%\s+packet\s+loss', stdout, re.IGNORECASE)
            if loss_match:
                loss = float(loss_match.group(1))

            # Parse latency (avg)
            latency = 0.0
            # Linux: rtt min/avg/max/mdev = X/Y/Z/W ms
            lat_match = re.search(r'(?:rtt|round-trip).*?=\s*[\d.]+/([\d.]+)', stdout)
            if not lat_match:
                # Windows: Average = Xms
                lat_match = re.search(r'Average\s*=\s*([\d.]+)\s*ms', stdout, re.IGNORECASE)
                if not lat_match:
                    # Fallback: any ms value
                    lat_match = re.search(r'time[<=]([\d.]+)\s*ms', stdout, re.IGNORECASE)

            if lat_match:
                latency = float(lat_match.group(1))

            success = loss < 100.0
            return PingResult(host=host, success=success, latency_ms=latency,
                              packet_loss_pct=loss)
        except subprocess.TimeoutExpired:
            return PingResult(host=host, success=False, error="Ping timeout")
        except FileNotFoundError:
            return Pinger._socket_ping(host, count, timeout)
        except Exception as e:
            return PingResult(host=host, success=False, error=str(e))

    @staticmethod
    def _socket_ping(host: str, count: int = 5, timeout: int = 3) -> PingResult:
        """Fallback: TCP connect to port 80 or 443 to test reachability."""
        successes = 0
        latencies = []
        for _ in range(count):
            for port in [80, 443, 53]:
                try:
                    t0 = time.time()
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    s.connect((host, port))
                    s.close()
                    latencies.append((time.time() - t0) * 1000)
                    successes += 1
                    break
                except Exception:
                    continue
        loss = (1 - successes / count) * 100
        avg_lat = sum(latencies) / len(latencies) if latencies else 0
        return PingResult(host=host, success=successes > 0,
                          latency_ms=avg_lat, packet_loss_pct=loss)

# ─── Email Notifier ────────────────────────────────────────────────────────────
class EmailNotifier:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.enabled = cfg.get("enabled", False)

    def send(self, alert: Alert) -> bool:
        if not self.enabled:
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[ISP-MONITOR] {alert.level}: {alert.subject}"
            msg["From"]    = self.cfg["sender"]
            msg["To"]      = ", ".join(self.cfg["recipients"])

            level_color = {"CRITICAL": "#dc2626", "WARNING": "#ca8a04",
                           "RECOVERY": "#16a34a", "INFO": "#0891b2"}.get(alert.level, "#888")
            html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;background:#0d1117;color:#e6edf3;padding:20px">
<div style="max-width:600px;margin:0 auto;background:#161b22;border-radius:10px;overflow:hidden;border:1px solid #30363d">
  <div style="background:{level_color};padding:16px 24px">
    <h2 style="margin:0;color:#fff">⚠ {alert.level}: {alert.isp_name}</h2>
    <p style="margin:4px 0 0;color:rgba(255,255,255,.8);font-size:13px">{alert.timestamp}</p>
  </div>
  <div style="padding:24px">
    <h3 style="color:#e6edf3;margin-top:0">{alert.subject}</h3>
    <pre style="background:#0d1117;padding:16px;border-radius:6px;font-size:13px;color:#8b949e;border:1px solid #30363d;white-space:pre-wrap">{alert.body}</pre>
    <p style="color:#8b949e;font-size:12px;margin-bottom:0">🔐 ISP Monitor | Auto-generated by SRINIVASAN55/ISP-Monitor</p>
  </div>
</div></body></html>"""

            msg.attach(MIMEText(alert.body, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self.cfg["smtp_host"], self.cfg["smtp_port"], timeout=15) as s:
                s.ehlo(); s.starttls(); s.ehlo()
                s.login(self.cfg["sender"], self.cfg["password"])
                s.sendmail(self.cfg["sender"], self.cfg["recipients"], msg.as_string())
            return True
        except Exception as e:
            logging.error(f"Email send failed: {e}")
            return False

# ─── Monitor Core ──────────────────────────────────────────────────────────────
class ISPMonitor:
    def __init__(self, config: dict):
        self.config    = config
        self.thresh    = config["thresholds"]
        self.notifier  = EmailNotifier(config["email"])
        self.statuses: Dict[str, ISPStatus] = {}
        self.events: List[dict] = []
        self._lock     = threading.Lock()
        self._running  = True

        # Logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)-8s %(message)s",
            handlers=[
                logging.FileHandler(config["logging"]["log_file"]),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.log = logging.getLogger("ISPMonitor")

        # Init ISP status objects
        for isp in config["isps"]:
            self.statuses[isp["name"]] = ISPStatus(
                name=isp["name"], gateway=isp["gateway"]
            )

    def _log_event(self, event: dict):
        self.events.append(event)
        try:
            with open(self.config["logging"]["json_log"], "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception:
            pass

    def _check_isp(self, isp_cfg: dict) -> PingResult:
        """Ping primary gateway; if fails, try backup hosts."""
        result = Pinger.ping(
            isp_cfg["gateway"],
            count=self.thresh["ping_count"],
            timeout=self.thresh["ping_timeout_sec"]
        )
        if not result.success and isp_cfg.get("backup_hosts"):
            for backup in isp_cfg["backup_hosts"]:
                r2 = Pinger.ping(backup, count=3, timeout=self.thresh["ping_timeout_sec"])
                if r2.success:
                    # Partial — use backup result but mark degraded
                    r2.host = isp_cfg["gateway"]
                    r2.packet_loss_pct = max(r2.packet_loss_pct, 20)
                    return r2
        return result

    def _determine_state(self, status: ISPStatus, result: PingResult) -> str:
        """Determine ISP state from ping result."""
        if not result.success or result.packet_loss_pct >= 100:
            return "DOWN"
        if result.packet_loss_pct >= self.thresh["packet_loss_critical_pct"]:
            return "DEGRADED"
        if (result.latency_ms >= self.thresh["latency_critical_ms"] or
                result.packet_loss_pct >= self.thresh["packet_loss_warn_pct"]):
            return "DEGRADED"
        return "UP"

    def _should_alert(self, status: ISPStatus, level: str) -> bool:
        cooldown = self.config["email"]["alert_cooldown_min"] * 60
        return time.time() - status.last_alert_time > cooldown

    def _build_alert(self, status: ISPStatus, new_state: str, result: PingResult) -> Optional[Alert]:
        """Build alert message based on state transition."""
        prev = status.state

        if new_state == "DOWN" and prev != "DOWN":
            return Alert(
                isp_name=status.name,
                level="CRITICAL",
                subject=f"{status.name} is DOWN — No connectivity",
                body=(
                    f"ISP Link: {status.name}\n"
                    f"Gateway:  {status.gateway}\n"
                    f"Status:   DOWN (100% packet loss)\n"
                    f"Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Consecutive failures: {status.consecutive_failures + 1}\n"
                    f"Last seen UP: {status.last_up or 'Unknown'}\n\n"
                    f"ACTION REQUIRED: Verify physical link, check router/modem.\n"
                    f"Consider switching to {'ISP-2 (Backup)' if 'Primary' in status.name else 'ISP-1 (Primary)'}."
                )
            )
        elif new_state == "DEGRADED" and prev == "UP":
            level = "CRITICAL" if result.latency_ms >= self.thresh["latency_critical_ms"] else "WARNING"
            return Alert(
                isp_name=status.name,
                level=level,
                subject=f"{status.name} DEGRADED — High latency / Packet loss",
                body=(
                    f"ISP Link: {status.name}\n"
                    f"Gateway:  {status.gateway}\n"
                    f"Status:   DEGRADED\n"
                    f"Latency:  {result.latency_ms:.1f} ms (threshold: {self.thresh['latency_critical_ms']} ms)\n"
                    f"Loss:     {result.packet_loss_pct:.0f}%\n"
                    f"Time:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Monitor closely — possible congestion or partial link failure."
                )
            )
        elif new_state == "UP" and prev in ("DOWN", "DEGRADED"):
            downtime = ""
            if status.downtime_start:
                secs = int(time.time() - status.downtime_start)
                downtime = f"{secs//3600:02d}h:{(secs%3600)//60:02d}m:{secs%60:02d}s"
            return Alert(
                isp_name=status.name,
                level="RECOVERY",
                subject=f"{status.name} RECOVERED — Link is back UP",
                body=(
                    f"ISP Link: {status.name}\n"
                    f"Gateway:  {status.gateway}\n"
                    f"Status:   UP ✓\n"
                    f"Latency:  {result.latency_ms:.1f} ms\n"
                    f"Loss:     {result.packet_loss_pct:.0f}%\n"
                    f"Downtime: {downtime or 'N/A'}\n"
                    f"Recovered: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Link has recovered. No further action needed."
                )
            )
        return None

    def _process_result(self, isp_cfg: dict, result: PingResult):
        name   = isp_cfg["name"]
        status = self.statuses[name]
        new_state = self._determine_state(status, result)

        # Update consecutive counters
        if result.success and result.packet_loss_pct < 100:
            status.consecutive_failures = 0
            status.consecutive_successes += 1
        else:
            status.consecutive_failures += 1
            status.consecutive_successes = 0

        # Only flip state after N consecutive failures (avoid flapping)
        effective_state = new_state
        if new_state == "DOWN" and status.consecutive_failures < self.thresh["consecutive_failures"]:
            effective_state = status.state  # Don't flip yet

        # State transition
        prev_state = status.state
        if effective_state != prev_state:
            if effective_state == "DOWN" and prev_state != "DOWN":
                status.last_down = datetime.now().isoformat()
                status.downtime_start = time.time()
                status.alert_sent = False
            elif effective_state in ("UP",) and prev_state in ("DOWN", "DEGRADED"):
                status.last_up = datetime.now().isoformat()
                status.downtime_start = None

        status.state = effective_state
        status.latency_ms = result.latency_ms
        status.packet_loss_pct = result.packet_loss_pct

        # Record history
        status.history.append({
            "ts": result.timestamp, "state": effective_state,
            "latency": result.latency_ms, "loss": result.packet_loss_pct
        })

        # Log event
        event = {
            "timestamp": result.timestamp, "isp": name,
            "state": effective_state, "prev_state": prev_state,
            "latency_ms": result.latency_ms, "loss_pct": result.packet_loss_pct
        }
        self._log_event(event)

        # Alerts
        if effective_state != prev_state or (effective_state in ("DOWN","DEGRADED") and self._should_alert(status, effective_state)):
            alert = self._build_alert(status, effective_state, result)
            if alert and self._should_alert(status, alert.level):
                status.last_alert_time = time.time()
                self._send_alert(alert)

    def _send_alert(self, alert: Alert):
        color = {"CRITICAL": C.RED+C.BOLD, "WARNING": C.YELLOW,
                 "RECOVERY": C.GREEN, "INFO": C.CYAN}.get(alert.level, C.RESET)
        self.log.warning(f"[{alert.level}] {alert.isp_name}: {alert.subject}")
        print(f"\n{'─'*60}")
        print(f"{color}  ⚠  {alert.level}: {alert.subject}{C.RESET}")
        print(f"{'─'*60}")
        print(alert.body)
        print(f"{'─'*60}\n")
        sent = self.notifier.send(alert)
        if sent:
            self.log.info(f"Email alert sent to: {self.config['email']['recipients']}")

    def _print_dashboard(self):
        """Print live dashboard to terminal."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\033[2J\033[H", end="")  # Clear screen
        print(BANNER)
        print(f"  {C.BOLD}Last Update: {now}{C.RESET}")
        print(f"  {'─'*62}")
        for name, status in self.statuses.items():
            state_color = {"UP": C.GREEN, "DOWN": C.RED+C.BOLD,
                           "DEGRADED": C.YELLOW, "UNKNOWN": C.CYAN}.get(status.state, C.RESET)
            state_str = f"{state_color}{'●':>2} {status.state:<10}{C.RESET}"
            lat_str   = f"{status.latency_ms:>7.1f} ms" if status.state != "DOWN" else "   ---    "
            loss_str  = f"{status.packet_loss_pct:>5.0f}% loss"
            down_str  = f"  {C.RED}({status.uptime_str}){C.RESET}" if status.state == "DOWN" else ""
            print(f"  {C.BOLD}{name:<25}{C.RESET} {state_str} {lat_str}  {loss_str}{down_str}")

            # Mini sparkline from history
            if status.history:
                pts = list(status.history)[-20:]
                bar = ""
                for p in pts:
                    if p["state"] == "DOWN":    bar += f"{C.RED}▼{C.RESET}"
                    elif p["state"] == "DEGRADED": bar += f"{C.YELLOW}~{C.RESET}"
                    else: bar += f"{C.GREEN}▲{C.RESET}"
                print(f"    History: {bar}")
        print(f"\n  {C.CYAN}Check interval: {self.thresh['check_interval_sec']}s  |  "
              f"Ping count: {self.thresh['ping_count']}  |  "
              f"Email alerts: {'ON' if self.config['email']['enabled'] else 'OFF'}{C.RESET}")
        print(f"  Press Ctrl+C to stop\n")

    def _monitor_isp(self, isp_cfg: dict):
        """Thread worker: continuously monitors one ISP."""
        name = isp_cfg["name"]
        self.log.info(f"[{name}] Monitor thread started → {isp_cfg['gateway']}")
        while self._running:
            result = self._check_isp(isp_cfg)
            with self._lock:
                self._process_result(isp_cfg, result)
            time.sleep(self.thresh["check_interval_sec"])

    def run(self):
        print(BANNER)
        self.log.info("ISP Monitor starting...")
        self.log.info(f"Monitoring {len(self.config['isps'])} ISP(s)")

        # Start one thread per ISP (staggered start)
        threads = []
        for i, isp in enumerate(self.config["isps"]):
            t = threading.Thread(target=self._monitor_isp, args=(isp,), daemon=True)
            t.start()
            threads.append(t)
            time.sleep(2)  # Stagger checks

        # Dashboard refresh loop
        try:
            while self._running:
                with self._lock:
                    self._print_dashboard()
                time.sleep(5)
        except KeyboardInterrupt:
            self.log.info("Stopping ISP Monitor...")
            self._running = False
        finally:
            self._save_summary()

    def _save_summary(self):
        summary = {
            "generated": datetime.now().isoformat(),
            "isps": [
                {"name": s.name, "gateway": s.gateway, "final_state": s.state,
                 "last_up": s.last_up, "last_down": s.last_down}
                for s in self.statuses.values()
            ]
        }
        with open("isp_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\n{C.GREEN}[✓] Summary saved: isp_summary.json{C.RESET}")

# ─── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="ISP-Monitor — Dual ISP Uptime & Latency Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python isp_monitor.py                          # Use default config
  python isp_monitor.py --config my_config.json # Custom config file
  python isp_monitor.py --generate-config       # Write sample config to disk
  python isp_monitor.py --isp1 192.168.1.1 --isp2 10.0.0.1  # Quick mode
        """
    )
    parser.add_argument("--config",          help="Path to JSON config file")
    parser.add_argument("--generate-config", action="store_true", help="Write sample config.json and exit")
    parser.add_argument("--isp1",            help="ISP-1 gateway IP (quick mode)")
    parser.add_argument("--isp2",            help="ISP-2 gateway IP (quick mode)")
    parser.add_argument("--interval",        type=int, default=30, help="Check interval in seconds")
    parser.add_argument("--smtp-host",       help="SMTP server for email alerts")
    parser.add_argument("--smtp-user",       help="SMTP username/sender email")
    parser.add_argument("--smtp-pass",       help="SMTP password/app password")
    parser.add_argument("--recipients",      nargs="+", help="Alert recipient emails")
    args = parser.parse_args()

    if args.generate_config:
        with open("config.json", "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        print(f"{C.GREEN}[✓] Sample config written to config.json{C.RESET}")
        print(f"    Edit it and run: python isp_monitor.py --config config.json")
        return

    # Load config
    config = DEFAULT_CONFIG.copy()
    if args.config and os.path.exists(args.config):
        with open(args.config) as f:
            config.update(json.load(f))

    # Quick mode overrides
    if args.isp1:
        config["isps"][0]["gateway"] = args.isp1
    if args.isp2:
        config["isps"][1]["gateway"] = args.isp2
    if args.interval:
        config["thresholds"]["check_interval_sec"] = args.interval
    if args.smtp_host:
        config["email"]["smtp_host"] = args.smtp_host
        config["email"]["enabled"] = True
    if args.smtp_user:
        config["email"]["sender"] = args.smtp_user
    if args.smtp_pass:
        config["email"]["password"] = args.smtp_pass
    if args.recipients:
        config["email"]["recipients"] = args.recipients

    monitor = ISPMonitor(config)
    monitor.run()

if __name__ == "__main__":
    main()
