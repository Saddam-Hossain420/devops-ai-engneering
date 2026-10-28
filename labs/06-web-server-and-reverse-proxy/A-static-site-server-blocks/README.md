# Lab 06-A — Static site ও server block

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৬০ মিনিট |
| **Environment** | Ubuntu VM (nginx); offline config যাচাই যেকোনো OS-এ |
| **Label** | 🖥️ VM — `/etc/nginx` ও `/var/www`-এ পরিবর্তন; snapshot নিন |
| **Tested** | `check_a.py`-এর offline অংশ Windows-এ যাচাই করা হয়েছে: একটি reference config-এ (repo-তে রাখা হয়নি) ALL PASS, ভুল config-এ FAIL। Live অংশে একটি false PASS ধরা ও ঠিক করা হয়েছে (nginx না থাকা "444" নয়)। **আসল nginx-এ `--live` চালানো হয়নি।** |

## Objective

একটি VM-এ দুটি static site (`site-a.lab`, `site-b.lab`) ও একটি নিরাপদ catch-all server বানানো। প্রতিটি request কোথায় যাবে, তা আগে [`server_select.py`](../../../06-web-server-and-reverse-proxy/code/L06-03/server_select.py) দিয়ে **অনুমান** করবেন, তারপর আসল nginx-এ মেলাবেন।

## Prerequisites

- [L06-02](../../../06-web-server-and-reverse-proxy/L06-02-nginx-architecture.md), [L06-03](../../../06-web-server-and-reverse-proxy/L06-03-nginx-server-blocks.md)

## Environment setup

```bash
sudo apt install nginx
mkdir -p ~/lab06a
for s in site-a site-b; do
  sudo mkdir -p /var/www/$s && echo "<h1>$s</h1>" | sudo tee /var/www/$s/index.html >/dev/null
  echo "SECRET=do-not-serve" | sudo tee /var/www/$s/.env >/dev/null
done
```

File: [`check_a.py`](check_a.py)।

## Steps

1. `~/lab06a/lab06a.conf` লিখুন (L06-03-এর `sites.conf` দেখে, কিন্তু copy না করে)। লাগবে:
   - Port ৮০-এর `default_server`, যা `return 444`।
   - `site-a.lab` ও `site-b.lab` — প্রতিটির নিজের `root`, `location / { try_files $uri $uri/ =404; }`, এবং hidden file-এর deny।
2. **Offline যাচাই:** `python3 check_a.py ~/lab06a/lab06a.conf` → ALL PASS।
3. **অনুমান:** নিচের ছয়টি request-এর জন্য কাগজে লিখুন কোন server ও location মিলবে, তারপর `server_select.py` দিয়ে যাচাই করুন:
   - `site-a.lab /`
   - `site-b.lab /`
   - `SITE-A.LAB. /`
   - `site-a.lab /.env`
   - `site-a.lab /nope`
   - IP দিয়ে `/`
4. **Deploy:**

   ```bash
   sudo cp ~/lab06a/lab06a.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/lab06a.conf /etc/nginx/sites-enabled/
   sudo rm -f /etc/nginx/sites-enabled/default
   sudo nginx -t && sudo systemctl reload nginx
   ```

5. **Live যাচাই:** `python3 check_a.py ~/lab06a/lab06a.conf --live`।
6. ধাপ ৩-এর প্রতিটি request `curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: …' http://127.0.0.1/…` দিয়েও চালিয়ে অনুমানের সাথে মেলান।

## Expected behavior

| Request | ফল |
|---|---|
| `site-a.lab /` | `<h1>site-a</h1>` |
| `site-a.lab /.env` | 403 |
| `site-a.lab /nope` | 404 |
| অজানা Host / IP | Response ছাড়াই connection বন্ধ (curl: `Empty reply from server`) |

## Verification

```bash
python3 check_a.py ~/lab06a/lab06a.conf --live; echo "exit=$?"     # ALL CHECKS PASSED, 0
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ |
|---|---|
| `duplicate default server` | Ubuntu-র `sites-enabled/default` এখনো আছে |
| সব Host-এ site-a | `server_name`-এ typo, বা catch-all নেই |
| `.env` download হয় | Hidden-file location নেই, বা আগের location জিতছে (L06-03-এর ক্রম) |
| 403 index-এ | `/var/www/...`-এর permission (www-data পড়তে পারে?) |
| `--live`-এ সব FAIL, `ConnectionRefusedError` | nginx চলছে না (`systemctl status nginx`) |

## Cleanup / reset

```bash
sudo rm -f /etc/nginx/sites-enabled/lab06a.conf /etc/nginx/sites-available/lab06a.conf
sudo rm -rf /var/www/site-a /var/www/site-b
sudo nginx -t && sudo systemctl reload nginx
```

## Assessment

1. ধাপ ৩-এর কোন অনুমান ভুল ছিল, কেন?
2. Catch-all না থাকলে IP-এর request কোন site-এ যেত? `sites-enabled`-এর file-এর নাম বদলালে কী হতো?
3. `return 444` বনাম `return 404` — কোনটা কখন?
4. `.env` সুরক্ষার location-টি কোন location-এর আগে বা পরে থাকলে কাজ করত না?
