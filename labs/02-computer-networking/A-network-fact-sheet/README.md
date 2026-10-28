# Lab 02-A — Network fact sheet: নিজের machine-এর network পূর্ণ মানচিত্র

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৬০–৭৫ মিনিট |
| **Environment** | Ubuntu VM (বা Ubuntu machine), Python 3.10+ |
| **Label** | — (সব read-only; কোনো system পরিবর্তন নয়) |

## Objective

নিজের machine-এর network-কে প্রতিটি স্তরে পর্যবেক্ষণ করে একটি এক পাতার **fact sheet** তৈরি: interface ও MAC, IP ও subnet, gateway ও route, DNS-এর পথ, শোনা port ও connection, path MTU, এবং একটি HTTPS endpoint-এর স্তরভিত্তিক সময়। প্রতিটি তথ্য একটি native command **ও** এই module-এর একটি Python tool দিয়ে মিলিয়ে।

## Prerequisites

- Lesson: [L02-01](../../../02-computer-networking/L02-01-network-models.md) থেকে [L02-09](../../../02-computer-networking/L02-09-dhcp-icmp-mtu.md), [L02-16](../../../02-computer-networking/L02-16-troubleshooting-toolkit.md)
- `iproute2`, `dnsutils`, `curl` (Ubuntu-তে সাধারণত আছে; `dig` না থাকলে `sudo apt install dnsutils`)

## Environment setup

```bash
cd ~/devops-ai-engineering/02-computer-networking/code
mkdir -p ~/devops-notebook/labs/02-A
```

## Steps

1. **Interface ও L2** (L02-02):

   ```bash
   ip -br link; ip -br addr
   ip neigh > ~/devops-notebook/labs/02-A/neigh.txt
   python3 L02-02/l2_tool.py neigh ~/devops-notebook/labs/02-A/neigh.txt
   ```

   Primary interface-এর MAC — unicast/universal (`l2_tool.py mac <MAC>`)?

2. **Subnet** (L02-03): নিজের IP/prefix নিয়ে `python3 L02-03/subnet_calc.py info <IP/prefix>` — network, broadcast, কয়টি host? IP private কোন range-এ?

3. **Route** (L02-04):

   ```bash
   ip route > ~/devops-notebook/labs/02-A/routes.txt
   python3 L02-04/route_nat.py lookup ~/devops-notebook/labs/02-A/routes.txt 1.1.1.1
   ip route get 1.1.1.1
   ```

   দুটো একই gateway ও interface বলে?

4. **DNS-এর পথ** (L02-06):

   ```bash
   cat /etc/resolv.conf; resolvectl status | head -15
   python3 L02-06/dns_wire.py query example.com A           # system resolver
   python3 L02-06/dns_wire.py query example.com A --server 1.1.1.1
   dig example.com; getent hosts example.com
   ```

   আপনার stub resolver কোন address-এ, আর আসল upstream কোনটি? দুটি query-র TTL তুলনা করুন।

5. **Socket** (L02-05):

   ```bash
   ss -tan > ~/devops-notebook/labs/02-A/ss.txt
   python3 L02-05/ss_summary.py ~/devops-notebook/labs/02-A/ss.txt
   sudo ss -ltnp
   ```

   কোন কোন service কোন address-এ শুনছে? কোনোটি `0.0.0.0`-এ থাকার দরকার আছে কি?

6. **Path MTU** (L02-09):

   ```bash
   python3 L02-09/mtu_calc.py ping-size
   ping -M do -s 1472 -c 2 1.1.1.1; tracepath -n 1.1.1.1 | tail -3
   ```

7. **একটি HTTPS endpoint, স্তর ধরে** (L02-07, L02-08, L02-16):

   ```bash
   python3 L02-16/netcheck.py https://example.com/
   curl -s -o /dev/null -w 'dns %{time_namelookup} tcp %{time_connect} tls %{time_appconnect} ttfb %{time_starttransfer}\n' https://example.com/
   python3 L02-08/tls_inspect.py inspect example.com
   ```

8. **Fact sheet লিখুন** `~/devops-notebook/labs/02-A/fact-sheet.md`-এ: প্রতিটি তথ্যের পাশে কোন command থেকে পাওয়া।

## Expected behavior

- প্রতিটি Python tool-এর ফল native command-এর সাথে মেলে (না মিললে কেন — সেটাই শেখার বিষয়)।
- Fact sheet-এ অন্তত: interface, MAC, IP/prefix, network, gateway, default route-এর interface, stub ও upstream resolver, ৩টি listening socket ও তাদের address, path MTU, example.com-এর চার স্তরের সময়।

## Verification

```bash
test -s ~/devops-notebook/labs/02-A/fact-sheet.md && echo "fact sheet written"
grep -Eci 'gateway|resolver|mtu|listen' ~/devops-notebook/labs/02-A/fact-sheet.md   # ≥ 4
python3 L02-16/netcheck.py https://example.com/ --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["ok"])'   # True
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `dns_wire.py query` timeout | Network-এ UDP 53 বাইরে বন্ধ | `--server` দিয়ে system resolver ব্যবহার; organization-এর নীতি দেখুন |
| `ping -M do` "message too long" | Local interface MTU ১৫০০-এর কম | `ip link`-এ MTU দেখে `mtu_calc.py ping-size --mtu N` |
| `ss -ltnp`-এ process নেই | sudo ছাড়া চালানো | `sudo ss -ltnp` |
| `resolvectl` নেই | systemd-resolved ব্যবহার হচ্ছে না | `/etc/resolv.conf` সরাসরি দেখুন |

## Cleanup / reset

কিছু পরিবর্তন হয়নি। Notebook-এর file রেখে দিন — Lab C ও Milestone 2-এ তুলনার জন্য কাজে লাগবে।

## Assessment

1. আপনার machine থেকে `1.1.1.1`-এ একটি packet-এর প্রথম তিনটি hop কী (interface, gateway, NAT কোথায়)?
2. Stub resolver ও upstream resolver আলাদা কেন? `dig` ও `getent` কখন ভিন্ন উত্তর দিতে পারে?
3. কোন listening socket প্রয়োজনের বেশি exposed — কীভাবে কমাবেন?
4. example.com-এ সময়ের সবচেয়ে বড় অংশ কোন স্তরে, এবং দ্বিতীয়বার চালালে কোনটি কমে কেন?
