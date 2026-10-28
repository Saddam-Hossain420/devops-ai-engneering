# Module 02 Quiz — Computer Networking

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৭৫ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর answer key। Part B-তে calculator চলবে, কিন্তু module-এর tool নয় — পরে tool দিয়ে নিজের উত্তর যাচাই করুন। Part C-এর জন্য Ubuntu VM লাগবে।

মোট নম্বর: ৬০ (Part A ২০ + Part B ২০ + Part C ২০)

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. Encapsulation কী? HTTP request Ethernet-এ পৌঁছানো পর্যন্ত কোন কোন header যোগ হয়?
2. ARP কী সমস্যা সমাধান করে, এবং এটি কেন router পার হয় না?
3. `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` — এরা কী, এবং `192.0.2.0/24` কী জন্য?
4. Routing table-এ একাধিক route মিললে কোনটি জেতে?
5. NAT gateway-এর পেছনের বহু server বাইরে বহু connection খুললে কোন সম্পদ ফুরিয়ে যেতে পারে?
6. TCP ও UDP-র দুটি মূল পার্থক্য; DNS সাধারণত কোনটি ব্যবহার করে এবং কখন অন্যটি?
7. Server-এ অনেক `CLOSE-WAIT` — কার দোষ এবং কী অর্থ?
8. Recursive resolver ও authoritative server-এর পার্থক্য।
9. DNS-এ "propagation" আসলে কী?
10. `dig` ও `getent hosts` কখন ভিন্ন উত্তর দেয়?
11. HTTP/1.1-এ response body-র শেষ বোঝার তিনটি উপায়।
12. HTTP/2 কোন সমস্যা সমাধান করে; HTTP/3 কেন UDP-র উপর?
13. TLS client verify-এর সময় কোন চারটি জিনিস যাচাই করে?
14. Browser-এ কাজ করে কিন্তু `curl`-এ "unable to get local issuer certificate" — সম্ভাব্য কারণ।
15. "ছোট request কাজ করে, বড়টা ঝুলে থাকে" — সবচেয়ে সম্ভাব্য কারণ ও কোন ICMP বার্তা এতে জড়িত?
16. Stateful ও stateless firewall-এর পার্থক্য; AWS-এ কোনটি কোনটি?
17. WireGuard-এর AllowedIPs কোন দুটি কাজ করে?
18. L4 ও L7 load balancer-এর পার্থক্য; gRPC কেন L4-এ অসমভাবে ছড়ায়?
19. Network namespace, veth pair ও bridge — Docker container-এর network-এ প্রতিটির ভূমিকা।
20. 502 ও 504-এর পার্থক্য; proxy-তে connect timeout ও read timeout কেন আলাদা?

## Part B — Calculation ও analysis (প্রতিটি ২ নম্বর)

21. `10.20.0.0/22`: network, broadcast, ব্যবহারযোগ্য host সংখ্যা, এবং AWS subnet হলে কতটি ব্যবহারযোগ্য?
22. VPC `10.0.0.0/16`-কে `/20` subnet-এ ভাগ করলে কয়টি subnet, প্রতিটিতে কয়টি address, প্রথম তিনটি কী?
23. Peering-এর পরিকল্পনা: VPC A `10.0.0.0/16`, VPC B `10.0.128.0/17`। সম্ভব? কেন?
24. Routing table:

    ```text
    default via 192.168.1.1 dev eth0
    10.0.0.0/8 via 10.8.0.1 dev wg0
    10.20.0.0/16 via 192.168.1.254 dev eth0
    ```

    `10.20.5.9`, `10.99.1.1` ও `8.8.8.8` — প্রতিটি কোন পথে যাবে?
25. Underlay MTU ১৫০০, তার উপর VXLAN overlay (overhead ৫০)। ভেতরের MTU, TCP MSS (IPv4, option ছাড়া), এবং DF সহ সর্বোচ্চ `ping -s`?
26. MTU ১৫০০-এ `ping -s 4000` (DF ছাড়া, IPv4) — কয়টি fragment, প্রতিটির data আকার?
27. DHCP lease ৩৬০০ সেকেন্ড — client কখন renew ও কখন rebind চেষ্টা করবে?
28. একটি A record-এর TTL ৩৬০০। আপনি ১০:০০-এ IP বদলালেন। একটি resolver ৯:৪০-এ উত্তরটি cache করেছিল। সেই resolver সর্বশেষ কখন পুরোনো IP দিতে পারে? কী করলে এটা এড়ানো যেত?
29. ৯টি cache node-এ ১০ম node যোগ করা হলো। `hash % N` ও consistent hashing-এ আনুমানিক কত শতাংশ key অন্য node-এ যাবে?
30. tcpdump-এ দেখলেন:

    ```text
    IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [P.], seq 2001, ack 7001, win 64240, length 300
    IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [P.], seq 2001, ack 7001, win 64240, length 300
    IP 10.0.0.10.80 > 10.0.0.5.51514: Flags [.], seq 7001, ack ????, win 65160, length 0
    ```

    দ্বিতীয় লাইন কী, এবং server-এর ack নম্বর কত হবে?

## Part C — Practical (Ubuntu VM-এ)

31. (৫ নম্বর) [Lab 02-C](../../labs/02-computer-networking/C-broken-request-path/README.md) সম্পূর্ণ করুন; `check.sh`-এর output, মোট সময়, এবং কোন প্রমাণ দুটি timeout-কে আলাদা করল তা লিখুন।
32. (৫ নম্বর) `dig +trace` দিয়ে নিজের পছন্দের একটি domain-এর delegation chain, এবং একই নামের জন্য `dig`, `getent hosts`, `resolvectl query`-এর উত্তর ও TTL তুলনা।
33. (৫ নম্বর) L02-13-এর `netns_lab.sh` চালিয়ে `test` output, এবং `sudo tcpdump -ni br-lab` দিয়ে red → blue ping-এর ARP ও ICMP — capture-এর প্রথম ছয় লাইন ব্যাখ্যা সহ।
34. (৫ নম্বর) নিজের lab CA দিয়ে একটি HTTPS endpoint (Lab 02-B বা আলাদা) এবং `netcheck.py --cafile`-এর চার স্তরের PASS output; তারপর ইচ্ছাকৃতভাবে ভুল hostname দিয়ে TLS FAIL ও তার `openssl s_client` প্রমাণ।

---

<details>
<summary><strong>Answer key</strong></summary>

**Part A**

1. প্রতিটি স্তর নিজের header যোগ করে নিচের স্তরে দেয়: HTTP → TCP header (port, seq) → IP header (address, TTL) → Ethernet header (MAC, EtherType) + trailer।
2. একই LAN-এ IP থেকে MAC বের করে; broadcast-ভিত্তিক, আর broadcast router পার হয় না — অন্য network-এর জন্য gateway-র MAC লাগে।
3. RFC 1918 private range (Internet-এ route হয় না); `192.0.2.0/24` documentation (TEST-NET-1) — উদাহরণে ব্যবহারের জন্য, কোথাও পৌঁছায় না।
4. Longest prefix match (সবচেয়ে নির্দিষ্ট); সমান হলে কম metric।
5. Source port (প্রতি গন্তব্য IP:port-এ ~৬৪ হাজার) — NAT port exhaustion।
6. TCP: connection, নির্ভরযোগ্য ও ক্রমিক; UDP: connectionless, নিশ্চয়তা নেই। DNS: UDP ৫৩; বড় উত্তর (truncated) বা zone transfer-এ TCP।
7. Application-এর — অপর পক্ষ বন্ধ করেছে কিন্তু local app socket `close()` করছে না (leak)।
8. Recursive: client-এর পক্ষে খোঁজে ও cache করে; authoritative: zone-এর আসল উত্তর দেয় (AA flag)।
9. বিশ্বের resolver-দের cache-এ পুরোনো record-এর TTL একে একে শেষ হওয়া — কোনো সক্রিয় "ছড়ানো" নয়।
10. `/etc/hosts`-এ entry থাকলে বা nsswitch-এ অন্য source থাকলে — `dig` সরাসরি DNS, `getent` application-এর পথ।
11. `Content-Length`, `Transfer-Encoding: chunked`, connection বন্ধ।
12. HTTP/2: একটি connection-এ multiplexing (HTTP-স্তরের head-of-line blocking নেই), header compression; HTTP/3: TCP-র head-of-line blocking (একটি loss সব stream থামায়) এড়াতে QUIC/UDP, দ্রুত handshake।
13. Chain trusted root পর্যন্ত, মেয়াদ, hostname SAN-এ, ব্যবহার (serverAuth/CA flag)।
14. Server intermediate certificate পাঠাচ্ছে না (browser cache থেকে পূরণ করে), বা internal CA client-এর trust store-এ নেই।
15. MTU/PMTUD black hole; ICMP type ৩ code ৪ (IPv6: Packet Too Big) block হচ্ছে।
16. Stateful connection মনে রাখে, উত্তর স্বয়ংক্রিয় অনুমোদিত; stateless প্রতিটি packet আলাদা। Security group stateful, NACL stateless।
17. পাঠানোর সময় routing (কোন peer-এ), গ্রহণের সময় source যাচাই (ACL)।
18. L4: connection স্তরে, payload দেখে না; L7: request স্তরে, path/header routing। gRPC একটি দীর্ঘ HTTP/2 connection-এ বহু request — L4 পুরো connection একটি backend-এ দেয়।
19. Namespace = container-এর আলাদা network stack; veth = container-এর `eth0` ও host-এর `vethX`-এর জোড়া; bridge (`docker0`) = host-এর virtual switch যেখানে সব veth যুক্ত ও gateway।
20. 502: backend-এ connect ব্যর্থ বা অবৈধ উত্তর; 504: backend-এর উত্তরে timeout। আলাদা timeout না থাকলে ধীর connect (বা refused-এ দেরি) 504 দেখায় → ভুল diagnosis।

**Part B**

21. Network `10.20.0.0`, broadcast `10.20.3.255`, ১০২২ host; AWS-এ ১০১৯ (৫টি সংরক্ষিত)।
22. ২^(২০−১৬) = **১৬**টি subnet, প্রতিটিতে ২^১২ = **৪০৯৬** address; `10.0.0.0/20`, `10.0.16.0/20`, `10.0.32.0/20`।
23. **না** — `10.0.128.0/17` পুরোটাই `10.0.0.0/16`-এর ভেতরে (overlap); peering overlapping CIDR route করতে পারে না।
24. `10.20.5.9` → `10.20.0.0/16` via 192.168.1.254 (eth0) — /16 > /8; `10.99.1.1` → `10.0.0.0/8` via wg0; `8.8.8.8` → default via 192.168.1.1।
25. ১৫০০ − ৫০ = **১৪৫০**; MSS ১৪৫০ − ৪০ = **১৪১০**; ping `-s` ১৪৫০ − ২৮ = **১৪২২**।
26. L4 = ৪০০০ + ৮ = ৪০০৮ byte; প্রতি fragment সর্বোচ্চ ১৪৮০ → **৩টি**: ১৪৮০, ১৪৮০, ১০৪৮।
27. T1 = ৫০% = **১৮০০ s** (renew), T2 = ৮৭.৫% = **৩১৫০ s** (rebind)।
28. ৯:৪০ + ৬০ মিনিট = **১০:৪০** পর্যন্ত পুরোনো IP। পরিবর্তনের অন্তত এক পুরোনো-TTL আগে TTL কমিয়ে (যেমন ৩০০) রাখলে; পুরোনো server-ও কিছুক্ষণ চালু রাখা।
29. Modulo: প্রায় **৯০%** (N/(N+1)); consistent hashing: প্রায় **১০%** (১/(N+1))। (এই module-এর simulation: ৮৯.৬% ও ১০.৬%।)
30. দ্বিতীয় লাইন একই seq ও length = **retransmission** (প্রথমটি বা তার ACK হারিয়েছে); ack = ২০০১ + ৩০০ = **২৩০১**।

**Part C — গ্রহণযোগ্য উত্তরের বৈশিষ্ট্য:** আসল command ও output; Lab C-তে প্রথম timeout-এর প্রমাণ ভুল IP (`curl -v`-এর `Trying 192.0.2.123`, `getent`), দ্বিতীয়টির প্রমাণ `tcpdump -ni lo`-এ উত্তরহীন SYN ও `nft list ruleset`-এর drop rule, তৃতীয়টির `ss -ltnp`-এ `127.0.0.2` — fix-এ firewall বন্ধ বা `0.0.0.0` নয়; dig +trace-এ root → TLD → authoritative ও TTL-এর পার্থক্যের ব্যাখ্যা (cache); netns capture-এ ARP request/reply তারপর ICMP echo; netcheck-এর TLS FAIL বার্তা ও `openssl s_client`-এর verify error মেলানো।

</details>
