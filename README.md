<div align="center">

<img src="https://capsule-render.vercel.app/api?type=rect&color=gradient&customColorList=11&height=80&text=📡%20ISP-Monitor&fontSize=34&fontColor=ffffff" width="100%"/>

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![No Dependencies](https://img.shields.io/badge/stdlib-only-green?style=for-the-badge)]()
[![Platform](https://img.shields.io/badge/Linux%20%7C%20Windows%20%7C%20macOS-cross--platform-blue?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**Dual ISP uptime & latency monitor with email alerting.**  
Monitors two ISP connections simultaneously, detects outages and latency spikes, and emails your IT team automatically — built entirely on Python stdlib.

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 📡 **Dual ISP Monitoring** | Monitors two ISP links simultaneously in separate threads |
| 🏓 **Smart Ping** | System ping with backup host fallback — avoids false positives |
| ⏱️ **Latency Tracking** | Measures avg latency per check; alerts on spikes |
| 📉 **Packet Loss Detection** | Tracks loss% and alerts on degradation |
| 📧 **Email Alerts** | HTML + plain text emails to IT team (Gmail, SMTP) |
| 🔄 **State Transitions** | UP → DOWN, UP → DEGRADED, DOWN → RECOVERY alerts |
| 🛡️ **Flap Prevention** | N consecutive failures before state change (no alert spam) |
| 📊 **Live Dashboard** | Real-time terminal dashboard with sparkline history |
| 📄 **JSON + Log Files** | Structured event log + human-readable log file |
| ⚙️ **Config File** | JSON config for thresholds, SMTP, ISP IPs |

---

## 🚀 Quick Start

```bash
git clone https://github.com/SRINIVASAN55/ISP-Monitor.git
cd ISP-Monitor

# Run with defaults (monitors 8.8.8.8 and 1.1.1.1)
python isp_monitor.py

# Quick mode — specify your ISP gateways
python isp_monitor.py --isp1 192.168.1.1 --isp2 10.0.0.1

# With email alerts
python isp_monitor.py \
  --isp1 192.168.1.1 \
  --isp2 10.0.0.1 \
  --smtp-host smtp.gmail.com \
  --smtp-user your@gmail.com \
  --smtp-pass YOUR_APP_PASS \
  --recipients it@company.com noc@company.com

# Generate config file
python isp_monitor.py --generate-config
# Edit config.json, then:
python isp_monitor.py --config config.json
```

---

## 📊 Live Dashboard

```
  ISP-1 (Primary)          ● UP         12.3 ms    0% loss
    History: ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

  ISP-2 (Backup)           ● DEGRADED  245.1 ms   20% loss
    History: ▲▲▲▲▲▲▲▲~~~~~~~~~~▲▲
```

---

## 📧 Email Alert Sample

```
Subject: [ISP-MONITOR] CRITICAL: ISP-1 (Primary) is DOWN

ISP Link: ISP-1 (Primary)
Gateway:  192.168.1.1
Status:   DOWN (100% packet loss)
Time:     2024-01-15 10:32:01

Consecutive failures: 3
Last seen UP: 2024-01-15 10:30:45

ACTION REQUIRED: Verify physical link, check router/modem.
Consider switching to ISP-2 (Backup).
```

---

## ⚙️ Configuration

| Parameter | Default | Description |
|---|---|---|
| `latency_warn_ms` | 100 | Latency warning threshold |
| `latency_critical_ms` | 300 | Latency critical threshold |
| `packet_loss_critical_pct` | 30 | Packet loss % for critical alert |
| `consecutive_failures` | 3 | Failures before DOWN state |
| `check_interval_sec` | 30 | How often to ping |
| `alert_cooldown_min` | 15 | Min minutes between repeat alerts |

---

## 📄 License

MIT License © 2024 [Srinivasan S](https://github.com/SRINIVASAN55)
