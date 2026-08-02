# ISP-Monitor

Dual-ISP uptime and latency monitor with email alerting. Built for home labs and small offices running failover setups.

---

## The Setup It's Designed For

```
          ┌─────────────┐
          │   Router    │
          └──────┬──────┘
         ┌───────┴────────┐
    ISP-1 (Primary)    ISP-2 (Backup)
    Jio Fiber          Airtel 4G
    100 Mbps           40 Mbps
```

ISP-Monitor pings both uplinks every 30 seconds, logs latency, and fires an alert the moment either one drops — before your users notice.

---

## Prerequisites

| Requirement | Details |
|-------------|---------|
| Python | 3.8 or higher |
| OS | Linux, macOS, Windows |
| Network | Access to both ISP gateway IPs |
| SMTP | Optional — only needed for email alerts |

```bash
python3 --version    # must be 3.8+
```

---

## Installation

```bash
git clone https://github.com/SRINIVASAN55/ISP-Monitor.git
cd ISP-Monitor
pip install -r requirements.txt
```

---

## Running It

### Quickest start — no config file needed
```bash
# Monitor two ISP gateways directly
python3 isp_monitor.py --isp1 192.168.1.1 --isp2 192.168.2.1
```
Pass your ISP-1 and ISP-2 gateway IPs directly. Starts monitoring immediately.

### Generate a config file first (recommended)
```bash
python3 isp_monitor.py --generate-config
```
Creates a `config.json` file in the current directory. Edit it with your gateway IPs, SMTP details, and alert settings, then run:
```bash
python3 isp_monitor.py --config config.json
```

### Custom check interval
```bash
# Check every 10 seconds instead of default 30
python3 isp_monitor.py --isp1 192.168.1.1 --isp2 192.168.2.1 --interval 10

# Check every 60 seconds (lighter load)
python3 isp_monitor.py --config config.json --interval 60
```

### With email alerts
```bash
python3 isp_monitor.py   --isp1 192.168.1.1   --isp2 192.168.2.1   --smtp-host smtp.gmail.com   --smtp-user you@gmail.com   --smtp-pass your_app_password   --recipients alert@yourteam.com ops@yourteam.com
```
> For Gmail, use an **App Password**, not your regular password. Create one at myaccount.google.com → Security → App Passwords.

---

## All CLI Flags

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `--config` | Path to JSON config file | — | `--config config.json` |
| `--generate-config` | Write sample config.json and exit | — | `--generate-config` |
| `--isp1` | ISP-1 gateway IP (quick mode) | — | `--isp1 192.168.1.1` |
| `--isp2` | ISP-2 gateway IP (quick mode) | — | `--isp2 192.168.2.1` |
| `--interval` | Check interval in seconds | `30` | `--interval 10` |
| `--smtp-host` | SMTP server for email alerts | — | `--smtp-host smtp.gmail.com` |
| `--smtp-user` | SMTP username / sender email | — | `--smtp-user you@gmail.com` |
| `--smtp-pass` | SMTP password / app password | — | `--smtp-pass xxxx` |
| `--recipients` | Alert recipient emails (space-separated) | — | `--recipients a@b.com c@d.com` |

---

## Terminal Output

```
ISP Monitor  |  2024-01-15 14:23:01
─────────────────────────────────────────────
ISP-1  Jio Fiber    ● UP    12ms   99.97% (30d)
ISP-2  Airtel 4G   ● UP    38ms   98.41% (30d)

Last failover: 2024-01-12 03:14 → 03:19 (5 min) — ISP-1 outage
```

---

## Troubleshooting

**`No route to host` for ISP gateway**
→ Make sure you're using the correct gateway IP. Run `ip route` (Linux) or `route print` (Windows) to find it.

**Email alerts not sending**
→ Double-check SMTP credentials. For Gmail you must use an App Password. Test with: `python3 -c "import smtplib; s=smtplib.SMTP_SSL('smtp.gmail.com',465); s.login('you@gmail.com','apppass'); print('OK')"`

**Monitor keeps showing ISP as DOWN even when it's up**
→ Your gateway may block ICMP (ping). Try using `8.8.8.8` (Google DNS) or `1.1.1.1` (Cloudflare) as the target IPs instead.

**Run as a background service (Linux)**
```bash
nohup python3 isp_monitor.py --config config.json &
# or use systemd / screen / tmux for persistence
```

---

**Author:** S. Srinivasan · [GitHub](https://github.com/SRINIVASAN55) · [LinkedIn](https://linkedin.com/in/srinivasan132)
