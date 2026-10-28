# Ubuntu বনাম Fedora — cheat sheet

এই repository-র primary OS **Ubuntu**। নিচের পার্থক্যগুলো Fedora-তে practice করার সময় কাজে লাগবে।

## Package management

| কাজ | Ubuntu | Fedora |
|---|---|---|
| Package index update | `sudo apt update` | `sudo dnf check-update` (install-এর সময় স্বয়ংক্রিয় metadata refresh) |
| Install | `sudo apt install nginx` | `sudo dnf install nginx` |
| Remove | `sudo apt remove nginx` | `sudo dnf remove nginx` |
| System upgrade | `sudo apt upgrade` | `sudo dnf upgrade` |
| Package search | `apt search nginx` | `dnf search nginx` |
| কোন package-এ file আছে | `dpkg -S /usr/bin/dig` | `rpm -qf /usr/bin/dig` |
| Installed package-এর file | `dpkg -L nginx` | `rpm -ql nginx` |
| Package format | `.deb` | `.rpm` |
| History / undo | `/var/log/apt/history.log` | `dnf history`, `dnf history undo <id>` |

## Package নামের পার্থক্য

| Tool | Ubuntu package | Fedora package |
|---|---|---|
| dig, nslookup | `dnsutils` | `bind-utils` |
| ip | `iproute2` | `iproute` |
| mtr | `mtr-tiny` | `mtr` |
| Compiler toolchain | `build-essential` | `gcc make` (বা `@development-tools` group) |
| Python venv | `python3-venv` | (built-in) |

## Firewall

| কাজ | Ubuntu (ufw) | Fedora (firewalld) |
|---|---|---|
| অবস্থা | `sudo ufw status verbose` | `sudo firewall-cmd --state`, `--list-all` |
| Port খোলা | `sudo ufw allow 80/tcp` | `sudo firewall-cmd --add-port=80/tcp --permanent && sudo firewall-cmd --reload` |
| Service খোলা | `sudo ufw allow 'Nginx Full'` | `sudo firewall-cmd --add-service=http --permanent` |

দুটোর নিচেই kernel-এ nftables কাজ করে: `sudo nft list ruleset`।

## Mandatory access control

| বিষয় | Ubuntu: AppArmor | Fedora: SELinux |
|---|---|---|
| অবস্থা | `sudo aa-status` | `getenforce`, `sestatus` |
| Denial log | `journalctl -k | grep -i apparmor` | `sudo ausearch -m avc -ts recent` |
| Model | path-ভিত্তিক profile | label (context)-ভিত্তিক |
| সাধারণ fix | profile আপডেট | `restorecon`, `semanage fcontext`, `setsebool` |

কখনো "সমস্যা সমাধানে" AppArmor/SELinux পুরোপুরি বন্ধ করবেন না — কারণ খুঁজে নির্দিষ্ট fix দিন।

## Service ও system

| বিষয় | Ubuntu | Fedora |
|---|---|---|
| Admin group | `sudo` | `wheel` |
| Nginx config | `/etc/nginx/sites-available/` + `sites-enabled/` symlink | `/etc/nginx/conf.d/*.conf` |
| Web server user | `www-data` | `nginx` |
| Default container tool | Docker (install করতে হয়) | Podman (preinstalled) |
| Auto updates | `unattended-upgrades` | `dnf-automatic` |
| Release upgrade | `do-release-upgrade` | `dnf system-upgrade` |
| Network config | Netplan (`/etc/netplan/*.yaml`) → systemd-networkd/NetworkManager | NetworkManager (`nmcli`) |

systemd, journald, `ip`, `ss`, `curl`, Python — দুটোতেই একই।
