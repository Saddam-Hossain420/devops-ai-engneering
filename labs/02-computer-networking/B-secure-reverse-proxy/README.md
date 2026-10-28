# Lab 02-B — Secure reverse proxy: TLS, load balancing ও firewall একসাথে

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ৯০–১২০ মিনিট |
| **Environment** | Ubuntu VM (snapshot নিন), দ্বিতীয় machine/VM থেকে পরীক্ষা হলে ভালো |
| **Label** | ⚠️ Nginx install, ufw চালু, `/etc/nginx/conf.d/lab02b.conf`, `~/lab02b/` — শেষে cleanup ধাপ অনুসরণ করুন। Remote VM-এ ufw চালুর আগে SSH allow করুন। |

## Objective

দুটি local backend-এর সামনে একটি **Nginx reverse proxy** বসানো, যা:

- নিজের lab CA-র certificate দিয়ে **HTTPS** দেয় (L02-08);
- backend-দের মধ্যে `least_conn` দিয়ে load balance করে এবং একটি বন্ধ হলেও কাজ চালিয়ে যায় (L02-12);
- প্রতিটি request-এ `X-Request-ID` যোগ করে access log-এ লেখে (L02-17);
- **শুধু ৪৪৩ ও ২২** বাইরে খোলা রাখে, backend-রা শুধু `127.0.0.1`-এ (L02-05, L02-10)।

তারপর প্রতিটি দাবি একটি command দিয়ে প্রমাণ করা।

## Prerequisites

- Lesson: [L02-07](../../../02-computer-networking/L02-07-http.md), [L02-08](../../../02-computer-networking/L02-08-tls-certificates.md), [L02-10](../../../02-computer-networking/L02-10-firewalls.md), [L02-12](../../../02-computer-networking/L02-12-load-balancing.md), [L02-15](../../../02-computer-networking/L02-15-packet-capture.md), [L02-16](../../../02-computer-networking/L02-16-troubleshooting-toolkit.md)

## Environment setup

```bash
sudo apt install nginx openssl curl tcpdump
mkdir -p ~/lab02b/b1 ~/lab02b/b2 ~/lab02b/tls && cd ~/lab02b
echo "backend-1" > b1/index.html; echo "backend-2" > b2/index.html
```

## Steps

1. **Backend** (শুধু loopback-এ):

   ```bash
   (cd b1 && python3 -m http.server 8001 --bind 127.0.0.1 >/dev/null 2>&1 &)
   (cd b2 && python3 -m http.server 8002 --bind 127.0.0.1 >/dev/null 2>&1 &)
   ss -ltn '( sport = :8001 or sport = :8002 )'
   ```

2. **Lab CA ও server certificate** (L02-08-এর Section 9.3/Exercise ১; VM-এর IP বা `lab02b.local` নাম SAN-এ):

   ```bash
   cd ~/lab02b/tls
   umask 077
   openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout ca.key -out ca.crt \
     -subj "/CN=Lab02B Root CA" -days 7 -addext basicConstraints=critical,CA:TRUE -addext keyUsage=critical,keyCertSign
   openssl req -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout server.key -out server.csr -subj "/CN=lab02b.local"
   printf 'subjectAltName=DNS:lab02b.local,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n' > ext.cnf
   openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 7 -extfile ext.cnf
   sudo install -d -m 0750 -o root -g www-data /etc/nginx/lab02b
   sudo install -m 0640 -o root -g www-data server.key server.crt /etc/nginx/lab02b/
   ```

   `ca.key` কোথাও copy করবেন না; lab শেষে মুছবেন।

3. **Nginx config** `/etc/nginx/conf.d/lab02b.conf`:

   ```nginx
   upstream lab02b_app {
       least_conn;
       server 127.0.0.1:8001 max_fails=1 fail_timeout=10s;
       server 127.0.0.1:8002 max_fails=1 fail_timeout=10s;
   }
   log_format lab02b '$remote_addr [$time_local] "$request" $status rid=$request_id up=$upstream_addr ut=$upstream_response_time';
   server {
       listen 443 ssl;
       server_name lab02b.local;
       ssl_certificate     /etc/nginx/lab02b/server.crt;
       ssl_certificate_key /etc/nginx/lab02b/server.key;
       ssl_protocols TLSv1.2 TLSv1.3;
       access_log /var/log/nginx/lab02b.log lab02b;
       location / {
           proxy_pass http://lab02b_app;
           proxy_set_header X-Request-ID $request_id;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_connect_timeout 1s;
           proxy_read_timeout 5s;
           add_header X-Request-ID $request_id always;
       }
   }
   ```

   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

4. **Firewall** (L02-10 — SSH আগে!):

   ```bash
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow OpenSSH
   sudo ufw allow 443/tcp
   sudo ufw enable
   sudo ufw status numbered
   ```

5. **প্রমাণ সংগ্রহ** (প্রতিটির output notebook-এ):

   ```bash
   cd ~/devops-ai-engineering/02-computer-networking/code
   echo "127.0.0.1 lab02b.local" | sudo tee -a /etc/hosts
   python3 L02-16/netcheck.py https://lab02b.local/ --cafile ~/lab02b/tls/ca.crt        # ৪টি PASS
   python3 L02-08/tls_inspect.py inspect lab02b.local --cafile ~/lab02b/tls/ca.crt      # issuer = Lab02B Root CA
   curl -s https://lab02b.local/ ; echo "exit=$?"                                        # CA ছাড়া: verify ব্যর্থ (exit 60)
   for i in $(seq 6); do curl -s --cacert ~/lab02b/tls/ca.crt https://lab02b.local/; done   # backend-1/2 পালাক্রমে
   sudo tail -6 /var/log/nginx/lab02b.log                                                 # rid ও up= কলাম
   ```

6. **Failover:** একটি backend বন্ধ করুন (`pkill -f 'http.server 8002'`), আবার ৬টি request — সব সফল? log-এ `up=` কী দেখায়?
7. **বাইরে থেকে exposure** (দ্বিতীয় machine থেকে, VM-এর IP দিয়ে): `nc -zv VM_IP 443` (খোলা), `nc -zv VM_IP 8001` (timeout বা refused — কেন?)।
8. **Encryption নিজের চোখে:** `sudo tcpdump -ni lo -A 'tcp port 443' -c 20` চালিয়ে একটি request — "backend-1" text দেখা যায়? তারপর `-ni lo 'tcp port 8001'`-এ একই — পার্থক্য কী এবং কেন ঠিক আছে?

## Expected behavior

- `netcheck.py` চারটি PASS; CA ছাড়া `curl` exit ৬০ (certificate verify failed)।
- ৬টি request দুই backend-এ ভাগ; একটি বন্ধ থাকলে সব যায় অন্যটিতে, কোনো 502 নয় (প্রথমটি ছাড়া হতে পারে — কেন? L02-12)।
- Access log-এর প্রতিটি লাইনে আলাদা `rid=`, এবং response header-এ একই ID।
- বাইরে থেকে শুধু ২২ ও ৪৪৩।

## Verification

```bash
python3 L02-16/netcheck.py https://lab02b.local/ --cafile ~/lab02b/tls/ca.crt --json | grep -q '"ok": true' && echo PASS-https
curl -sI --cacert ~/lab02b/tls/ca.crt https://lab02b.local/ | grep -i '^x-request-id' && echo PASS-request-id
ss -ltn '( sport = :8001 or sport = :8002 )' | grep -vq '127.0.0.1' || echo PASS-backends-loopback-only
sudo ufw status | grep -E '^(443|OpenSSH)' && echo PASS-firewall
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `nginx -t`: cannot load certificate key | Permission | `/etc/nginx/lab02b` group `www-data`, mode ০৬৪০ |
| 502 সব request-এ | Backend চলছে না | `ss -ltn`; Step 1 |
| `netcheck` TLS FAIL: Hostname mismatch | SAN-এ নাম নেই | Step 2-এর `ext.cnf` |
| বাইরে থেকে ৪৪৩ timeout | ufw বা cloud security group | `ufw status`; cloud-এ SG (L02-14) |
| SSH কেটে গেছে | ufw চালুর আগে SSH allow হয়নি | VM console থেকে `ufw allow OpenSSH` |

> **Fedora-তে:** `sudo dnf install nginx`; Nginx-এর user `nginx` (`www-data` নয়); firewall: `sudo firewall-cmd --add-service=https` (তারপর `--runtime-to-permanent`); SELinux-এ Nginx-কে backend port-এ connect করতে `sudo setsebool -P httpd_can_network_connect 1`, এবং certificate file-এর context: `sudo restorecon -Rv /etc/nginx/lab02b`।

## Cleanup / reset

```bash
pkill -f 'http.server 800[12]'
sudo rm -f /etc/nginx/conf.d/lab02b.conf /var/log/nginx/lab02b.log && sudo rm -rf /etc/nginx/lab02b
sudo systemctl reload nginx
sudo sed -i '/lab02b\.local/d' /etc/hosts
sudo ufw delete allow 443/tcp          # ufw চালু রাখতে চাইলে বাকি rule রাখুন; নইলে: sudo ufw disable
rm -rf ~/lab02b                        # lab CA-র private key সহ
```

## Assessment

1. প্রতিটি Objective-এর দাবির জন্য একটি প্রমাণ (command + output)।
2. Step 8-এ ৪৪৩-এ content দেখা যায়নি কিন্তু ৮০০১-এ গেছে — production-এ এটি কখন গ্রহণযোগ্য, কখন নয় (zero trust, L02-11)?
3. Backend-কে `127.0.0.1`-এ bind করা ও firewall — দুটোই কেন? (defense in depth)
4. `proxy_connect_timeout 1s` ও `proxy_read_timeout 5s` কেন আলাদা (L02-17)?
5. Lab CA-কে system trust store-এ না রেখে `--cafile` ব্যবহার করলাম কেন?
