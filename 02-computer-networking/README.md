# Module 02 — Computer Networking

**Stage:** 2 · **Lesson:** 17 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

OSI/TCP-IP model থেকে শুরু করে addressing, routing, NAT, TCP/UDP, DNS, HTTP, TLS, firewall, VPN, load balancing, Linux network namespace, cloud networking ও packet capture। শেষে একটি browser request DNS থেকে database পর্যন্ত কীভাবে যায় এবং প্রতিটি ধাপে কীভাবে failure diagnose করতে হয়।

## পূর্বশর্ত (Prerequisites)

[01-linux-systems](../01-linux-systems/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- CIDR ও subnet হিসাব করা (Python ipaddress দিয়েও)
- TCP handshake, connection state ও socket ব্যাখ্যা করা
- DNS resolution chain ও TLS handshake ব্যাখ্যা করা
- dig, curl, ss, ip, tcpdump, mtr দিয়ে layer-ভিত্তিক troubleshooting
- Network namespace দিয়ে isolated network তৈরি করা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L02-01 | [OSI ও TCP/IP model](L02-01-network-models.md) | Beginner |  | COMPLETED |
| L02-02 | [Ethernet, MAC address, ARP, switching ও VLAN](L02-02-ethernet-arp-vlan.md) | Beginner |  | COMPLETED |
| L02-03 | [IPv4, IPv6, CIDR ও subnetting](L02-03-ip-addressing-cidr.md) | Beginner |  | COMPLETED |
| L02-04 | [Routing table, gateway ও NAT](L02-04-routing-nat.md) | Intermediate |  | COMPLETED |
| L02-05 | [TCP, UDP, port, socket ও connection state](L02-05-tcp-udp-sockets.md) | Intermediate |  | COMPLETED |
| L02-06 | [DNS: recursive resolver, authoritative server ও caching](L02-06-dns.md) | Intermediate |  | COMPLETED |
| L02-07 | [HTTP/1.1, HTTP/2 ও HTTP/3](L02-07-http.md) | Intermediate |  | COMPLETED |
| L02-08 | [TLS, certificate ও HTTPS](L02-08-tls-certificates.md) | Intermediate |  | COMPLETED |
| L02-09 | [DHCP, ICMP, MTU ও path MTU discovery](L02-09-dhcp-icmp-mtu.md) | Intermediate |  | COMPLETED |
| L02-10 | [Firewall: nftables, ufw (Fedora-তে firewalld), security group ও NACL](L02-10-firewalls.md) | Intermediate | 🎩 | COMPLETED |
| L02-11 | [SSH tunnel, VPN, WireGuard ও zero-trust connectivity](L02-11-tunnels-vpn-zero-trust.md) | Advanced | 🔗 | COMPLETED |
| L02-12 | [Load balancing ও reverse proxy: L4 বনাম L7](L02-12-load-balancing.md) | Intermediate |  | COMPLETED |
| L02-13 | [Network namespace, veth pair ও bridge](L02-13-netns-veth-bridge.md) | Advanced |  | COMPLETED |
| L02-14 | [Cloud networking concept: VPC, subnet, routing, peering](L02-14-cloud-networking.md) | Intermediate |  | COMPLETED |
| L02-15 | [tcpdump ও Wireshark দিয়ে packet inspection](L02-15-packet-capture.md) | Intermediate |  | COMPLETED |
| L02-16 | [Troubleshooting toolkit: dig, curl, ss, ip, traceroute, mtr](L02-16-troubleshooting-toolkit.md) | Intermediate |  | COMPLETED |
| L02-17 | [Browser থেকে database পর্যন্ত: একটি request-এর পূর্ণ যাত্রা](L02-17-request-journey.md) | Intermediate |  | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `02-computer-networking/LNN-MM-slug.md`

## Labs

Lab folder: [labs/02-computer-networking/](../labs/02-computer-networking/README.md) · Module quiz: [assessments/02-computer-networking/quiz.md](../assessments/02-computer-networking/quiz.md)

- Level A — নিজের machine-এর network fact sheet: interface, subnet, route, DNS, socket, MTU, HTTPS timing
- Level B — Nginx reverse proxy: নিজের CA-র TLS, load balancing, request ID, ufw
- Level C — তিন স্তরে ভাঙা request path (DNS, firewall drop, ভুল bind address) diagnose

## সংশ্লিষ্ট project

—

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Request-flow diagram নিজে এঁকে ব্যাখ্যা
- [ ] চারটি network failure scenario-তে সঠিক layer চিহ্নিত করা

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
