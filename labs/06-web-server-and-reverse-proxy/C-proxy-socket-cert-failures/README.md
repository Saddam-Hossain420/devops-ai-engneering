# Lab 06-C — Upstream, socket ও certificate: তিন স্তরের ব্যর্থতা

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৬০–৯০ মিনিট |
| **Environment** | Ubuntu VM (nginx, systemd, openssl, python3) |
| **Label** | 🖥️ VM only — `break-it.sh` system unit ও nginx site বানায়; snapshot নিন |
| **Tested** | তিনটি script `bash -n`-এ পরিষ্কার এবং L04-07-এর `shlint_mini.py`-তে ০ finding। Guard (VM flag ছাড়া চালালে প্রত্যাখ্যান; setup না থাকলে check exit ২) Windows-এ যাচাই করা হয়েছে। script যে tool ব্যবহার করে (TaskFlow, `taskflow_serve.py`, `pki_lab.py`-এর মেয়াদোত্তীর্ণ certificate) আলাদাভাবে test করা। **পুরো break → fix → check VM-এ চালানো হয়নি।** |

## Objective

একজন user জানালেন: "`https://taskflow.example.com:8443/health` কাজ করছে না।" পথে তিনটি স্তরে তিনটি ব্যর্থতা আছে। একটি ঠিক করলে পরেরটি প্রকাশ পায় — বাস্তব incident-এর মতো। প্রতিটি নির্ণয় করবেন log ও tool দিয়ে, অনুমান করে নয়।

## Prerequisites

- [L06-04](../../../06-web-server-and-reverse-proxy/L06-04-reverse-proxy-upstream.md) (`error_explainer.py`)
- [L06-05](../../../06-web-server-and-reverse-proxy/L06-05-app-process-socket-systemd.md) (`socket_check.py`)
- [L06-07](../../../06-web-server-and-reverse-proxy/L06-07-nginx-tls-certificates.md) (`cert_expiry.py`)

## Environment setup

```bash
cd ~/devops-ai-engineering/labs/06-web-server-and-reverse-proxy/C-proxy-socket-cert-failures
sudo bash break-it.sh --yes-i-am-in-a-vm
```

Files: [`break-it.sh`](break-it.sh), [`check.sh`](check.sh), [`reset.sh`](reset.sh)।

এরা TaskFlow (`/opt/lab06c`), systemd unit `lab06c-app.service`, lab PKI (`/etc/lab06c/pki`) ও nginx site `lab06c` (port ৮৪৪৩) বানায়।

## Steps

1. Timer চালু করুন।
2. **Symptom:**

   ```bash
   curl -sv --cacert /etc/lab06c/pki/root.crt --resolve taskflow.example.com:8443:127.0.0.1 \
        https://taskflow.example.com:8443/health 2>&1 | tail -5
   sudo bash check.sh
   ```

3. **নির্ণয়ের tool:**

   ```bash
   T=~/devops-ai-engineering/06-web-server-and-reverse-proxy/code
   sudo tail -20 /var/log/nginx/error.log | python3 $T/L06-04/error_explainer.py -
   python3 $T/L06-07/cert_expiry.py --host 127.0.0.1:8443
   sudo python3 $T/L06-05/socket_check.py /run/lab06c/app.sock --user www-data
   ls -l /run/lab06c/; systemctl cat lab06c-app.service; journalctl -u lab06c-app -n 20
   ```

4. **একটি একটি করে ঠিক করুন।** System unit বদলালে `systemctl daemon-reload && systemctl restart lab06c-app`; nginx বদলালে `nginx -t && systemctl reload nginx`। প্রতিবার `sudo bash check.sh`।
5. শেষে `ALL CHECKS PASSED`।
6. Notebook-এ প্রতিটি ব্যর্থতার জন্য লিখুন: লক্ষণ, error.log-এর বার্তা, কোন tool ধরল, কোন lesson, fix।

## Expected behavior

| পরীক্ষা | ঠিক অবস্থায় |
|---|---|
| `nginx -t` | ঠিক |
| `/run/lab06c/app.sock` | `660`, group `www-data` |
| Served certificate | ৭ দিনের বেশি বৈধ |
| `GET /health` (TLS যাচাইসহ) | 200 |
| `POST /tasks` | 201 |

## Verification

```bash
sudo bash check.sh; echo "exit=$?"      # ALL CHECKS PASSED, 0
```

## Troubleshooting (সূত্র — একটি একটি করে খুলুন)

<details><summary>সূত্র ১ — curl বলছে "certificate has expired"</summary>

nginx কোন file serve করছে? `grep ssl_certificate /etc/nginx/sites-available/lab06c.conf`; `/etc/lab06c/pki/`-এ আর কী আছে? `cert_expiry.py` দিয়ে দুটো file-এর মেয়াদ তুলনা করুন (L06-07)। বদলানোর পরে reload।
</details>

<details><summary>সূত্র ২ — এখন 502, error.log-এ "(2: No such file or directory)"</summary>

nginx কোন socket খুঁজছে (`upstream`), আর app কোন socket বানিয়েছে (`ls /run/lab06c`, `systemctl cat lab06c-app`)? দুটো এক জায়গায় আনুন (L06-05)।
</details>

<details><summary>সূত্র ৩ — এখনো 502, এবার "(13: Permission denied)"</summary>

`socket_check.py`-এর verdict কী? Socket-এর mode কে ঠিক করে — app-এর কোন argument? (L06-05-এর `--mode`, `umask`)
</details>

## Cleanup / reset

```bash
sudo bash reset.sh       # শুধু /etc/lab06c/.lab06c চিহ্ন থাকলে
```

## Assessment

1. তিনটি ব্যর্থতার প্রতিটির লক্ষণ, error.log-এর বার্তা, ও fix।
2. ব্যর্থতাগুলো কেন একটির পর একটি প্রকাশ পেল (একসাথে নয়)? Client-এর দিক থেকে কোনটি প্রথম?
3. Certificate-এর ব্যর্থতা browser-এ দেখতে কেমন, আর API client-এ কেমন? কোন monitoring এটা আগেই ধরত (L06-07)?
4. এই ধরনের "ভুল socket নাম" deploy-এর সময় কীভাবে আটকানো যায়? (config-এর এক উৎস, deploy-এর পরে health check — L05-12)
