#!/usr/bin/env bash
# Lab 06-C: TaskFlow + nginx-এ তিনটি স্তরে তিনটি ইচ্ছাকৃত ব্যর্থতা তৈরি করে।
# ⚠️ শুধু snapshot-যুক্ত VM-এ। তৈরি করে: /opt/lab06c, /etc/lab06c, systemd unit lab06c-app.service,
#    nginx site lab06c (port 8443)। সব কিছু "lab06c" দিয়ে চিহ্নিত; reset.sh সব মোছে।
# Usage: sudo bash break-it.sh --yes-i-am-in-a-vm
set -euo pipefail

[[ "${1:-}" == "--yes-i-am-in-a-vm" ]] || { echo "refusing: run with --yes-i-am-in-a-vm (VM only)" >&2; exit 2; }
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 2; }
for cmd in nginx openssl python3 systemctl; do
  command -v "$cmd" >/dev/null || { echo "$cmd not found (sudo apt install nginx openssl python3)" >&2; exit 2; }
done
[[ -e /etc/lab06c ]] && { echo "refusing: /etc/lab06c exists — run reset.sh first" >&2; exit 2; }
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"

install -d -m 0755 /opt/lab06c /etc/lab06c
install -m 0644 "$REPO/05-python-for-infrastructure/code/L05-13/taskflow_api.py" /opt/lab06c/
install -m 0644 "$REPO/06-web-server-and-reverse-proxy/code/L06-05/taskflow_serve.py" /opt/lab06c/

# TLS: lab PKI — valid ও expired দুটোই; nginx-কে expired দেওয়া হবে (ব্যর্থতা ৩)
python3 "$REPO/06-web-server-and-reverse-proxy/code/L06-07/pki_lab.py" create --out /etc/lab06c/pki >/dev/null
chmod 0600 /etc/lab06c/pki/*.key
chmod 0644 /etc/lab06c/pki/root.crt

# ব্যর্থতা ১ ও ২: app ভুল নামে ও 0600 mode-এ socket বানায়
cat > /etc/systemd/system/lab06c-app.service <<'EOF'
# lab06c
[Unit]
Description=Lab 06-C TaskFlow app

[Service]
User=nobody
Group=www-data
RuntimeDirectory=lab06c
StateDirectory=lab06c
Environment=TASKFLOW_DB=/var/lib/lab06c/taskflow.db
ExecStart=/usr/bin/python3 /opt/lab06c/taskflow_serve.py --unix /run/lab06c/api.sock --mode 600
Restart=on-failure
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
EOF
systemctl daemon-reload
systemctl restart lab06c-app.service

cat > /etc/nginx/sites-available/lab06c.conf <<'EOF'
# lab06c
upstream lab06c_app {
    server unix:/run/lab06c/app.sock;
}
server {
    listen 8443 ssl;
    server_name taskflow.example.com;          # lab PKI-র certificate এই নামের জন্য
    ssl_certificate     /etc/lab06c/pki/expired-fullchain.pem;
    ssl_certificate_key /etc/lab06c/pki/server.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    location / {
        proxy_pass http://lab06c_app;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
# /etc/hosts বদলানো হয় না — client `curl --resolve taskflow.example.com:8443:127.0.0.1` ব্যবহার করে
ln -sf /etc/nginx/sites-available/lab06c.conf /etc/nginx/sites-enabled/lab06c.conf
touch /etc/lab06c/.lab06c
nginx -t && systemctl reload nginx

echo "Lab 06-C ready. Symptom:"
echo "  curl -sv --cacert /etc/lab06c/pki/root.crt --resolve taskflow.example.com:8443:127.0.0.1 https://taskflow.example.com:8443/health"
echo "Check:  sudo bash check.sh     Reset: sudo bash reset.sh"
