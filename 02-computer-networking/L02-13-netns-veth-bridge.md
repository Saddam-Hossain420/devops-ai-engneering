# L02-13 — Network namespace, veth pair ও bridge

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Advanced |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L01-16 — Namespace ও cgroup](../01-linux-systems/L01-16-namespaces-cgroups-capabilities.md), [L02-02 — Ethernet/ARP](L02-02-ethernet-arp-vlan.md), [L02-04 — Routing/NAT](L02-04-routing-nat.md), [L02-10 — Firewall](L02-10-firewalls.md) |
| **Label** | 🖥️ VM — host-এর network state বদলায়; শুধু lab VM-এ |
| **Tested** | `netns_inspect.py` ও `netns_lab.sh`: ৭টি test পাস — হাতে তৈরি `ip -j -d link` নমুনা থেকে topology ও finding, script-এর `bash -n` syntax, safety guard (confirmation ছাড়া ও root ছাড়া exit ২), প্রতিটি তৈরি object-এর মোছার পথ আছে কিনা (Python 3.14 + Git Bash, Windows)। **`netns_lab.sh up/test/down` আসলে চালানো হয়নি** — এর জন্য Linux kernel লাগে; Ubuntu VM-এ চালানো বাকি। Sample JSON-এর গঠন iproute2-এর JSON output-এর আদলে হাতে লেখা — Ubuntu-তে আসল `ip -j -d link`-এর সাথে মিলিয়ে দেখুন। |

---

## 1. এই lesson-এ যা শিখবেন

- **Network namespace**: আলাদা network stack — নিজস্ব interface, IP, routing table, firewall, port।
- **veth pair**: দুই প্রান্তের virtual cable — এক প্রান্ত এক namespace-এ, অপর প্রান্ত অন্যটিতে।
- **Linux bridge**: kernel-এর ভেতরে virtual switch (L02-02)।
- এই তিনটি + routing + NAT = **Docker-এর default bridge network**, এবং Kubernetes pod network-এর ভিত্তি।
- `ip netns`, `ip -n`, `nsenter` দিয়ে কাজ; কোন veth কোন container-এর তা খোঁজা।
- নিজের হাতে দুটি "container network" তৈরি, যাচাই ও পরিষ্কার মুছে ফেলা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L01-16-এ দেখেছেন container আসলে namespace ও cgroup দিয়ে আলাদা করা সাধারণ process। কিন্তু container-এর network কীভাবে কাজ করে?

- প্রতিটি container-এর নিজের `eth0`, নিজের `127.0.0.1`, একই port ৮০ একসাথে দশটি container-এ — কীভাবে?
- Container-গুলো একে অপরের সাথে ও Internet-এ কীভাবে কথা বলে?
- `docker run -p 8080:80` আসলে কী করে?
- Container-এর network কাজ না করলে host থেকে কোথায় দেখবেন?

এই lesson-এর পরে Docker networking (Module 10) ও Kubernetes CNI (Module 14) "জাদু" নয় — কয়েকটি `ip` command-এর স্বয়ংক্রিয় রূপ।

## 3. সহজ ভাষায় পরিচয়

```text
┌──── host namespace ─────────────────────────────────────────┐
│  ens3 192.168.56.10 (আসল NIC)                                │
│                                                             │
│  br-lab 10.200.0.1/24  ← virtual switch + gateway           │
│     ├── veth-red ════════════╗                              │
│     └── veth-blue ═══════╗   ║  (veth = দুই মাথার cable)    │
└─────────────────────────╫───╫───────────────────────────────┘
          ┌──── ns: blue ─╨─┐ ┌╨─── ns: red ────┐
          │ eth0 10.200.0.3 │ │ eth0 10.200.0.2 │
          │ lo 127.0.0.1    │ │ lo 127.0.0.1    │
          │ default via .1  │ │ default via .1  │
          └─────────────────┘ └─────────────────┘
```

| উপাদান | কী | Docker-এ সমতুল্য |
|---|---|---|
| Network namespace | আলাদা network stack | প্রতিটি container |
| veth pair | একদিকে যা ঢোকে, অন্যদিকে বের হয় | `vethXXXX` (host) ↔ `eth0` (container) |
| Bridge | Virtual L2 switch, MAC শেখে | `docker0` |
| Bridge-এর IP | Namespace-দের default gateway | `172.17.0.1` |
| `ip_forward` + masquerade | Namespace থেকে Internet | Docker-এর NAT rule |
| DNAT | Host port → namespace port | `-p 8080:80` |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### একটি ভবনে আলাদা অফিস

- **Namespace** = আলাদা অফিস — নিজস্ব টেলিফোন extension (port), নিজস্ব নোটিশ বোর্ড (routing table)। পাশের অফিসে extension ১০১ থাকলেও আপনার অফিসেও ১০১ থাকতে পারে।
- **veth pair** = অফিস থেকে ভবনের সুইচবোর্ড পর্যন্ত একটি তার — একপ্রান্তে যা বলবেন অন্যপ্রান্তে শোনা যাবে।
- **Bridge** = ভবনের সুইচবোর্ড — সব অফিসের তার এখানে, অফিসে অফিসে সংযোগ।
- **NAT** = ভবনের রিসেপশন — বাইরের ফোন রিসেপশনের নম্বর দিয়ে যায়।

### Analogy কোথায় মেলে না

- অফিসগুলো ভৌতভাবে আলাদা। Namespace-গুলো **একই kernel**-এ — kernel-এর bug বা ভুল capability (L01-16) পুরো আলাদাকরণ ভাঙতে পারে। Network namespace নিরাপত্তার একটি স্তর, পূর্ণ সীমানা নয় (VM শক্তিশালী)।
- তার কাটলে দুই প্রান্তই অকেজো, কিন্তু তার থেকে যায়। **veth-এর এক প্রান্ত মুছলে অপরটিও মুছে যায়**, এবং namespace মুছলে ভেতরের veth প্রান্ত ও তার জোড়া দুটোই চলে যায় — তাই cleanup সহজ (`netns_lab.sh down`)।
- সুইচবোর্ড শুধু সংযোগ দেয়। Linux bridge-এর traffic-এ netfilter rule-ও প্রভাব ফেলতে পারে (`br_netfilter`) — Kubernetes-এ এটি ইচ্ছাকৃতভাবে চালু করা হয়, এবং তখন bridge-এর ভেতরের traffic-ও firewall rule-এর অধীন।

## 5. Real-world engineering scenario — একটি container-এর network নেই

**পরিস্থিতি:** একটি host-এ ২০টি container; একটি container বাইরের API-তে পৌঁছাতে পারছে না, বাকিরা পারছে। Container-এর ভেতরে `ping`/`curl` tool নেই (minimal image)।

**Diagnosis — host থেকে, container image-এ tool ছাড়াই:**

```bash
PID=$(docker inspect -f '{{.State.Pid}}' api-7)
sudo nsenter -t "$PID" -n ip addr          # container-এর network namespace-এ host-এর ip tool
sudo nsenter -t "$PID" -n ip route         # default route আছে?
sudo nsenter -t "$PID" -n ss -tnp          # কোন connection কী অবস্থায় (L02-05)
# container-এর eth0-এর peer ifindex → host-এ কোন veth
sudo nsenter -t "$PID" -n cat /sys/class/net/eth0/iflink    # যেমন 9
ip -o link | grep '^9:'                                      # host-এর veth81bd0e4
ip -j -d link > links.json && python3 netns_inspect.py links.json
```

**পাওয়া গেল:** host-এর `veth81bd0e4` `docker0`-এর সদস্য কিন্তু `DOWN` — আগের দিন কেউ debug করতে গিয়ে `ip link set ... down` করে ভুলে গিয়েছিলেন। `netns_inspect.py` এটি সরাসরি ধরে ("is DOWN — the namespace behind it has no connectivity")।

**সমাধান:** `sudo ip link set veth81bd0e4 up` (বা container restart — Docker নতুন veth তৈরি করে)।

**শিক্ষা:** container-এর network সমস্যা host-এর `ip` দিয়ে, `nsenter` দিয়ে দেখা যায় — image-এ debugging tool রাখার দরকার নেই (এবং নিরাপত্তার জন্য না রাখাই ভালো)।

## 6. Diagram — একটি packet-এর পথ (red → Internet)

```text
ns red: app → socket → routing: default via 10.200.0.1 → eth0
         │ (veth: এক প্রান্তে ঢুকে অপর প্রান্তে বের হয়)
host:   veth-red → br-lab (bridge: dst MAC = br-lab নিজে) → host routing
         → ip_forward=1 → postrouting: masquerade src 10.200.0.2 → 192.168.56.10
         → ens3 → Internet
উত্তর:  ens3 → conntrack de-NAT (dst → 10.200.0.2) → routing: 10.200.0.0/24 dev br-lab
         → br-lab (ARP-এ শেখা MAC → veth-red port) → veth-red → eth0 (ns red) → app
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Network namespace | আলাদা network stack (interface, route, firewall, socket) |
| veth pair | জোড়া virtual interface — একটির ভেতরে যা পাঠানো হয় অন্যটি থেকে বের হয় |
| Bridge | Kernel-এর virtual L2 switch |
| Bridge port / master | Bridge-এ যুক্ত interface / যে bridge-এ যুক্ত |
| `ip netns` | Named namespace পরিচালনা (`/run/netns/NAME`) |
| `ip -n NAME` | ঐ namespace-এর ভেতরে `ip` চালানো |
| `nsenter -t PID -n` | একটি process-এর namespace-এ ঢোকা |
| `iflink` / `link_netnsid` | veth-এর peer-এর ifindex / peer কোন namespace-এ |
| `ip_forward` | Host-কে router হিসেবে কাজ করতে দেয় |
| Masquerade | Source NAT — বের হওয়ার interface-এর IP দিয়ে |
| CNI | Container Network Interface — Kubernetes-এ এই কাজগুলো করার plugin standard |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Namespace-এ কী কী আলাদা

প্রতিটি network namespace-এর নিজস্ব: interface তালিকা, IP address, routing table ও rule, ARP/neighbor table, netfilter (nftables) rule, socket ও port space, `/proc/sys/net` sysctl-এর বড় অংশ। নতুন namespace-এ শুধু `lo` থাকে, এবং সেটিও `DOWN` — তাই script-এ `ip -n red link set lo up` (নইলে namespace-এর ভেতরে `127.0.0.1`-ও কাজ করবে না)।

`ip netns add red` একটি file তৈরি করে `/run/netns/red` (bind mount) যেন কোনো process না থাকলেও namespace টিকে থাকে। Docker নিজের namespace এখানে নিবন্ধন করে না — তাই `ip netns list`-এ Docker container দেখা যায় না; `nsenter -t PID` লাগে।

### 8.2 veth ও bridge

- `ip link add veth-red type veth peer name eth0 netns red` — একটি command-এ জোড়া তৈরি এবং এক প্রান্ত সরাসরি namespace-এ।
- `ip link set veth-red master br-lab` — host প্রান্তকে bridge-এর port বানানো। Bridge-এর port-এর নিজের IP থাকে না; IP থাকে bridge-এ (gateway) ও namespace প্রান্তে।
- Bridge MAC learning করে (`bridge fdb show`) — L02-02-এর switch-এর মতো।

### 8.3 Docker ও Kubernetes-এ একই জিনিস

- `docker network create` = নতুন bridge (`br-<id>`); `docker run` = namespace + veth + bridge port + IP (Docker-এর IPAM) + `/etc/resolv.conf`।
- `-p 8080:80` = host-এ DNAT rule (`8080` → `172.17.0.2:80`) — এজন্যই L02-10-এ ufw-কে পাশ কাটায়।
- Kubernetes: প্রতিটি **pod** একটি network namespace (pod-এর সব container এটি share করে — তাই একই pod-এ `localhost` দিয়ে কথা বলা যায়); CNI plugin (bridge, Calico, Cilium…) veth ও route তৈরি করে; node-এর বাইরে overlay (VXLAN, L02-09) বা native routing।

### 8.4 Debugging-এর মৌলিক command

```bash
ip netns list
ip -n red addr; ip -n red route; ip -n red neigh
ip netns exec red ss -tlnp
bridge link show                    # কোন port কোন bridge-এ, অবস্থা
bridge fdb show br br-lab           # শেখা MAC
ip -d link show veth-red            # veth, master, peer
sudo nsenter -t PID -n <command>    # Docker/Kubernetes container
sudo tcpdump -ni br-lab             # bridge-এর সব traffic (L02-15)
sudo tcpdump -ni veth-red           # শুধু red-এর traffic
```

## 9. Practical demonstration

### 9.1 Topology inspector (যেকোনো machine-এ)

File: [`code/L02-13/netns_inspect.py`](code/L02-13/netns_inspect.py), [`sample-links.json`](code/L02-13/sample-links.json) — **হাতে তৈরি নমুনা** (iproute2-এর `ip -j -d link` JSON-এর আদলে; একটি Docker bridge ও এই lesson-এর lab bridge, ইচ্ছাকৃত দুটি সমস্যা সহ)।

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-13
python3 netns_inspect.py sample-links.json; echo "exit=$?"
```

**আসল output:**

```text
bridge docker0 172.17.0.1/16
  └─ veth3f2a9c1    UP    peer ifindex 6 in netns id 0
  └─ veth81bd0e4    UP    peer ifindex 8 in netns id 1
bridge br-lab 10.200.0.1/24
  └─ veth-red       UP    peer ifindex 2 in netns id 2
  └─ veth-blue      DOWN  peer ifindex 2 in netns id 3
(no bridge) veth-orphan peer veth-orphan-p in this namespace
(no bridge) veth-orphan-p peer veth-orphan in this namespace
- veth-blue on br-lab is DOWN — the namespace behind it has no connectivity
- veth-orphan is a veth without a bridge master — packets go nowhere unless routed
- veth-orphan-p is a veth without a bridge master — packets go nowhere unless routed
exit=1
```

- `veth-red` ও `veth-blue` দুটোরই peer ifindex ২ — কারণ প্রতিটি namespace-এর ভেতরে `lo` = ১, `eth0` = ২। ifindex **namespace-ভিত্তিক**, তাই peer চিনতে `link_netnsid`-ও লাগে।
- `veth-orphan` জোড়ার দুই প্রান্তই host-এ — কোনো কাজে যুক্ত নয়; প্রায়ই crash হওয়া container runtime-এর ফেলে যাওয়া আবর্জনা।

নিজের Ubuntu-তে: `ip -j -d link > links.json && python3 netns_inspect.py links.json` (Docker চললে docker0 দেখবেন)।

### 9.2 নিজের হাতে container network (⚠️ Ubuntu lab VM-এ, root)

File: [`code/L02-13/netns_lab.sh`](code/L02-13/netns_lab.sh) — `--yes-i-am-in-a-vm` ছাড়া কিছুই করে না; সব object-এর নামে `lab`; `down` শুধু নিজের তৈরি জিনিস মোছে এবং `--nat`-এর আগের `ip_forward` মান ফিরিয়ে দেয়।

```bash
sudo ./netns_lab.sh up --yes-i-am-in-a-vm
sudo ./netns_lab.sh test --yes-i-am-in-a-vm
```

**প্রত্যাশিত output (এই repository-তে চালানো হয়নি — Ubuntu VM-এ চালিয়ে নিজের output notebook-এ রাখুন):**

```text
namespace red: 10.200.0.2 via veth-red on br-lab
namespace blue: 10.200.0.3 via veth-blue on br-lab
PASS  red → bridge gateway (10.200.0.1)
PASS  red → blue (10.200.0.3) across the bridge
PASS  blue → red (10.200.0.2)
PASS  red has its own routing table (default via .1)
PASS  veth-red is a member of br-lab
PASS  eth0 exists inside red
PASS  host namespace does not own red's address
```

হাতে অন্বেষণ:

```bash
sudo ip netns exec red ip addr                     # শুধু lo ও eth0 — host-এর ens3 নেই
sudo ip netns exec red python3 -m http.server 80 & # red-এ port 80
sudo ip netns exec blue python3 -m http.server 80 &   # blue-তেও port 80 — কোনো সংঘর্ষ নেই!
curl -s 10.200.0.2 | head -3; curl -s 10.200.0.3 | head -3   # host থেকে দুটোই
sudo ip netns exec red ping -c1 1.1.1.1            # ব্যর্থ — NAT নেই
sudo kill %1 %2
sudo ./netns_lab.sh down --yes-i-am-in-a-vm
sudo ./netns_lab.sh up --nat --yes-i-am-in-a-vm    # এবার NAT সহ
sudo ./netns_lab.sh test --yes-i-am-in-a-vm        # internet test-ও PASS হওয়া উচিত
sudo nft list table ip netns_lab                   # masquerade rule
sudo ./netns_lab.sh down --yes-i-am-in-a-vm        # সব মুছে, ip_forward পুনরুদ্ধার
ip netns list; ip link show br-lab                 # কিছুই থাকা উচিত নয়
```

`-p 8080:80`-এর সমতুল্য (Exercise ৩): host-এ একটি DNAT rule।

> **Fedora-তে:** script একই (iproute2, nftables)। firewalld চালু থাকলে নতুন bridge-এর traffic firewalld-এর zone rule-এ আটকাতে পারে — lab-এর সময় `sudo firewall-cmd --zone=trusted --add-interface=br-lab` (runtime) দিন, এবং lab শেষে `--remove-interface`।

### 9.3 Test

```bash
python3 -m unittest -v
```

[`test_l02_13.py`](code/L02-13/test_l02_13.py)-এর ৭টি test: topology (দুটি bridge, সদস্য, orphan), peer বর্ণনা, CLI exit code ও ভুল JSON; lab script-এর `bash -n`, confirmation ছাড়া প্রত্যাখ্যান, অজানা action প্রত্যাখ্যান, এবং প্রতিটি তৈরি object-এর (namespace, bridge, nftables table, state file) মোছার code আছে কিনা।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `set -euo pipefail` | কোনো command ব্যর্থ হলে থামে | আধা-তৈরি অবস্থায় এগিয়ে না যাওয়া |
| Guard + root check সবার আগে | কিছু পরিবর্তনের আগেই | Lab C (Module 01)-এর একই নীতি |
| `peer name eth0 netns "$ns"` | এক command-এ জোড়া + স্থানান্তর | Docker-এর মতো container-এ `eth0` নাম |
| `ip -n "$ns"` | namespace-এর ভেতরে কাজ | `ip netns exec`-এর সংক্ষিপ্ত রূপ |
| `$STATE` file | আগের `ip_forward` মান | Host-কে ঠিক আগের অবস্থায় ফেরানো |
| `down`-এ `|| true` | আগে থেকে না থাকলেও চলে | Idempotent cleanup |
| `netns_inspect.kind` | `linkinfo.info_kind` | veth/bridge চেনা (`-d` flag লাগে) |
| `link_netnsid` | peer অন্য namespace-এ কিনা | ifindex namespace-ভিত্তিক |

**Python কেন এখানে, কোথায় নয়:** JSON output বিশ্লেষণ ও রিপোর্টে Python; network object তৈরিতে সরাসরি `ip` command (shell) — Python-এ wrapper লিখলে শুধু জটিলতা বাড়ে। Production-এ এই কাজ container runtime ও CNI plugin করে।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `netns_lab.sh test` | সব PASS (NAT ছাড়া internet test নেই) |
| দুই namespace-এ একই port ৮০ | দুটোই চলে |
| `bridge link show` | `veth-red`, `veth-blue` → `br-lab` |
| `down`-এর পরে `ip netns list` | খালি |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Namespace-এ `127.0.0.1`-ও কাজ করে না | `lo` DOWN | `ip -n red link show lo` | `ip -n red link set lo up` |
| Gateway-তে ping হয় না | veth host প্রান্ত DOWN বা bridge-এ নেই | `bridge link show`, `netns_inspect.py` | `ip link set ... up master br-lab` |
| Namespace থেকে internet নেই | `ip_forward=0`, masquerade নেই, firewall FORWARD drop | `sysctl net.ipv4.ip_forward`, `nft list ruleset` | `--nat`; ufw-এর forward policy |
| Docker চালু host-এ lab-এর forward কাজ করে না | Docker-এর FORWARD chain policy drop | `iptables -S FORWARD` | Lab bridge-এর জন্য accept rule (শুধু VM-এ) |
| `RTNETLINK answers: File exists` | আগের lab মোছা হয়নি | `ip netns list`, `ip link show br-lab` | `netns_lab.sh down` |
| Docker container `ip netns list`-এ নেই | Docker `/run/netns`-এ নিবন্ধন করে না | — | `nsenter -t PID -n` |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Network namespace আলাদা করে কিন্তু একই kernel — privileged container বা `CAP_NET_ADMIN` থাকলে network ভাঙা যায় (L01-16); `--network host` container namespace-এর সুরক্ষা পুরো বাদ দেয়; একই bridge-এর container-রা default-এ একে অপরের সাথে কথা বলতে পারে — আলাদা network বা Kubernetes NetworkPolicy; lab-এ `ip_forward` চালু রেখে দেওয়া host-কে router বানায় — `down` তাই পুনরুদ্ধার করে।
- **Performance:** veth + bridge + NAT প্রতিটি packet-এ কিছু CPU খরচ; খুব উচ্চ throughput-এ `--network host`, macvlan/ipvlan বা eBPF-ভিত্তিক CNI (Cilium); overlay-এর MTU (L02-09)।
- **Cost:** সরাসরি নয়; Kubernetes-এ CNI-এর পছন্দ (overlay বনাম cloud-native VPC routing) IP address ব্যবহার ও cross-AZ traffic খরচে প্রভাব ফেলে (Module 14)।

## 14. Hands-on exercise

1. `netns_lab.sh`-এ তৃতীয় namespace `green` যোগ করুন; test-এ green ↔ red যোগ করুন।
2. দুটি **আলাদা** bridge (`br-a`, `br-b`) — namespace দুটি কি সরাসরি কথা বলতে পারে? Host-এ routing ও firewall দিয়ে নির্দিষ্ট port-এ অনুমতি দিন (L02-10)।
3. `-p 8080:80`-এর সমতুল্য: host-এ `nft add table ip lab_dnat` … `tcp dport 8080 dnat to 10.200.0.2:80` — অন্য machine থেকে host-এর ৮০৮০-তে `curl`। শেষে table মুছুন।
4. Docker থাকলে: একটি container চালিয়ে Section 5-এর `nsenter` ও `iflink` পদ্ধতিতে তার host veth খুঁজুন; `netns_inspect.py`-এর output-এর সাথে মেলান।
5. `tcpdump -ni br-lab` চালিয়ে red → blue ping-এর ARP ও ICMP দেখুন (L02-15-এর preview)।

## 15. Mini-project — "docker network inspect" নিজের হাতে

একটি Python script যা `ip -j -d link`, `ip -j addr`, `bridge -j fdb` এবং (থাকলে) `docker inspect` JSON মিলিয়ে একটি table দেয়: container নাম → PID → host veth → bridge → IP → MAC → অবস্থা। শুধু read-only command। Module 10-এ Docker networking debug ও Module 14-এ CNI বোঝার সময় এটি কাজে লাগবে।

## 16. Interview প্রশ্ন

1. Network namespace কী এবং কী কী আলাদা করে?
2. veth pair কী? Docker container host-এর network-এ কীভাবে যুক্ত হয়?
3. Docker-এর default bridge network-এ container থেকে Internet-এ একটি packet-এর পথ বর্ণনা করুন।
4. `docker run -p 8080:80` kernel-স্তরে কী করে?
5. Container-এ debugging tool না থাকলে তার network কীভাবে পরীক্ষা করবেন?
6. Kubernetes pod-এর container-রা `localhost` দিয়ে কথা বলতে পারে কেন?

## 17. Self-assessment প্রশ্ন

1. অফিস analogy কোথায় মেলে না (তিনটি বিষয়)?
2. নতুন namespace-এ `lo` কেন নিজে up করতে হয়?
3. `veth-red` ও `veth-blue`-এর peer ifindex দুটোই ২ — কেন, এবং peer চিনতে আর কী লাগে?
4. `netns_lab.sh down` host-কে কীভাবে ঠিক আগের অবস্থায় ফেরায়?
5. Section 5-এর diagnosis-এ host-এর veth কীভাবে খুঁজে পাওয়া গেল?

## 18. সংক্ষিপ্ত সারাংশ

- Network namespace = আলাদা network stack; veth = দুই-মাথার virtual cable; bridge = virtual switch।
- Namespace + veth + bridge + routing + NAT = Docker bridge network; Kubernetes pod network-এর ভিত্তি।
- `ip -n`, `ip netns exec`, `nsenter -t PID -n`, `bridge link`, `iflink` দিয়ে debug।
- Namespace আলাদাকরণ একই kernel-এ — নিরাপত্তার একটি স্তর, পূর্ণ সীমানা নয়।
- Host-এর state বদলানো lab: guard, নামে চিহ্ন, idempotent ও পূর্ণ cleanup।

## 19. Completion checklist

- [ ] `netns_inspect.py` দিয়ে নিজের machine-এর topology দেখেছি
- [ ] VM-এ `netns_lab.sh up/test/down` চালিয়েছি, নিজের output notebook-এ রেখেছি
- [ ] দুই namespace-এ একই port চালিয়ে আলাদাকরণ দেখেছি
- [ ] (Docker থাকলে) একটি container-এর host veth খুঁজে পেয়েছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `ip-netns(8)`: https://man7.org/linux/man-pages/man8/ip-netns.8.html
- `veth(4)`: https://man7.org/linux/man-pages/man4/veth.4.html
- `network_namespaces(7)`: https://man7.org/linux/man-pages/man7/network_namespaces.7.html
- `nsenter(1)`: https://man7.org/linux/man-pages/man1/nsenter.1.html
- `bridge(8)`: https://man7.org/linux/man-pages/man8/bridge.8.html
- Docker — Bridge network driver: https://docs.docker.com/engine/network/drivers/bridge/
- Kubernetes — Cluster networking: https://kubernetes.io/docs/concepts/cluster-administration/networking/
- CNI specification: https://www.cni.dev/docs/spec/

---

**পরের lesson:** L02-14 — Cloud networking concept: VPC, subnet, routing, peering
