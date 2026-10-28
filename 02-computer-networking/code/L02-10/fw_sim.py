#!/usr/bin/env python3
"""Firewall simulator — host firewall (ordered, stateful), cloud security group (stateful, allow-only)
ও NACL (numbered, stateless)। শুধু standard library; কোনো আসল firewall rule বদলায় না।

Commands:
  python3 fw_sim.py eval sample-rules.txt --proto tcp --src 198.51.100.7 --dport 22
  python3 fw_sim.py audit sample-rules.txt        # shadowed/redundant rule ও internet-এ খোলা sensitive port
  python3 fw_sim.py demo                          # stateful বনাম stateless: NACL-এর ephemeral port ফাঁদ

Rule file format (হাতে তৈরি, nftables-এর সরলীকৃত রূপ), প্রতি লাইনে একটি:
  policy drop
  accept state established
  accept proto tcp dport 22 src 10.0.0.0/8
  accept proto tcp dport 80,443
  reject proto tcp dport 8000-8999
Exit: eval → 0 accept, 1 drop/reject; audit → 0 পরিষ্কার, 1 finding; 2 input error।
"""
from __future__ import annotations

import argparse
import ipaddress
import sys
from dataclasses import dataclass, field
from pathlib import Path

Net = ipaddress.IPv4Network | ipaddress.IPv6Network
PortRanges = list[tuple[int, int]] | None  # None = যেকোনো port

SENSITIVE = {22: "SSH", 3389: "RDP", 3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis",
             27017: "MongoDB", 9200: "Elasticsearch", 2375: "Docker API (no TLS)",
             10250: "kubelet", 11434: "Ollama LLM API"}
ANY4 = ipaddress.ip_network("0.0.0.0/0")


@dataclass(frozen=True)
class Packet:
    proto: str
    src: str
    dport: int = 0
    sport: int = 0
    dst: str = "192.0.2.10"


@dataclass
class Rule:
    action: str                      # accept | drop | reject
    proto: str | None = None         # None = any
    src: Net | None = None
    dports: PortRanges = None
    states: frozenset[str] | None = None
    line: int = 0
    text: str = ""

    def matches(self, p: Packet, state: str) -> bool:
        if self.proto and self.proto != p.proto:
            return False
        if self.src and ipaddress.ip_address(p.src) not in self.src:
            return False
        if self.dports is not None and not any(lo <= p.dport <= hi for lo, hi in self.dports):
            return False
        return self.states is None or state in self.states


def parse_ports(spec: str) -> list[tuple[int, int]]:
    out = []
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        a, b = int(lo), int(hi or lo)
        if not 0 <= a <= b <= 65535:
            raise ValueError(f"bad port range {part!r}")
        out.append((a, b))
    return out


def parse_rules(text: str) -> tuple[str, list[Rule]]:
    policy, rules = "accept", []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        words = line.split()
        if words[0] == "policy":
            if len(words) != 2 or words[1] not in ("accept", "drop"):
                raise ValueError(f"line {n}: policy accept|drop")
            policy = words[1]
            continue
        if words[0] not in ("accept", "drop", "reject"):
            raise ValueError(f"line {n}: unknown action {words[0]!r}")
        r = Rule(words[0], line=n, text=line)
        it = iter(words[1:])
        for key in it:
            val = next(it, None)
            if val is None:
                raise ValueError(f"line {n}: {key!r} needs a value")
            if key == "proto":
                r.proto = None if val == "any" else val
            elif key == "src":
                r.src = ipaddress.ip_network(val, strict=False)
            elif key == "dport":
                r.dports = parse_ports(val)
            elif key == "state":
                r.states = frozenset(val.split(","))
            else:
                raise ValueError(f"line {n}: unknown key {key!r}")
        rules.append(r)
    return policy, rules


class HostFirewall:
    """Input chain: উপর থেকে নিচে, প্রথম match জেতে; কেউ না মিললে policy। Conntrack দিয়ে stateful।"""

    def __init__(self, policy: str, rules: list[Rule]) -> None:
        self.policy, self.rules = policy, rules
        self.conntrack: set[tuple[str, str, int, str, int]] = set()

    def outbound(self, p: Packet) -> None:
        """Output policy accept ধরা হয়েছে; বের হওয়া flow মনে রাখা হয় যেন উত্তর 'established' হয়।"""
        self.conntrack.add((p.proto, p.dst, p.dport, p.src, p.sport))  # প্রত্যাশিত উত্তরের key

    def inbound(self, p: Packet) -> tuple[str, str]:
        state = "established" if (p.proto, p.src, p.sport, p.dst, p.dport) in self.conntrack else "new"
        for r in self.rules:
            if r.matches(p, state):
                return r.action, f"line {r.line}: {r.text}  [state {state}]"
        return self.policy, f"policy {self.policy}  [state {state}]"


@dataclass
class SecurityGroup:
    """Cloud security group: শুধু allow rule, ক্রম অর্থহীন, default deny, stateful (উত্তর সবসময় যায়)।"""
    inbound: list[Rule] = field(default_factory=list)

    def allows(self, p: Packet) -> bool:
        return any(r.matches(p, "new") for r in self.inbound)


@dataclass
class Nacl:
    """Subnet NACL: numbered rule, ছোট নম্বর আগে, allow ও deny দুটোই, stateless — উত্তরেও rule লাগে।"""
    inbound: list[tuple[int, Rule]] = field(default_factory=list)
    outbound: list[tuple[int, Rule]] = field(default_factory=list)

    def check(self, direction: str, p: Packet) -> tuple[str, str]:
        for num, r in sorted(self.inbound if direction == "in" else self.outbound, key=lambda x: x[0]):
            if r.matches(p, "new"):
                return r.action, f"rule {num}"
        return "drop", "rule * (implicit deny)"


def covers(a: Rule, b: Rule) -> bool:
    """a যে সব packet মেলে, b-র সব packet কি তার মধ্যে? (তাহলে a-র পরে b কখনো পৌঁছায় না)"""
    if a.proto and a.proto != b.proto:
        return False
    if a.src and (b.src is None or b.src.version != a.src.version or not b.src.subnet_of(a.src)):
        return False
    if a.dports is not None:
        if b.dports is None or not all(any(alo <= lo and hi <= ahi for alo, ahi in a.dports) for lo, hi in b.dports):
            return False
    return a.states is None or (b.states is not None and b.states <= a.states)


def audit(policy: str, rules: list[Rule]) -> list[str]:
    findings = []
    if policy == "accept":
        findings.append("policy accept: যা স্পষ্টভাবে বন্ধ নয় তা খোলা — default deny ব্যবহার করুন")
    for j, b in enumerate(rules):
        for a in rules[:j]:
            if covers(a, b):
                kind = "redundant" if a.action == b.action else "CONFLICT (never reached)"
                findings.append(f"line {b.line} {kind}: shadowed by line {a.line} ({a.text})")
                break
    for r in rules:
        if r.action != "accept" or r.states == frozenset({"established"}):
            continue
        if r.src is not None and r.src.prefixlen != 0:
            continue
        for port, name in SENSITIVE.items():
            if (r.proto in (None, "tcp")) and (r.dports is None or any(lo <= port <= hi for lo, hi in r.dports)):
                findings.append(f"line {r.line}: {name} ({port}) open to the whole internet")
    return findings


def demo() -> int:
    client = Packet("tcp", "203.0.113.7", dport=443, sport=51514, dst="10.0.1.20")
    reply = Packet("tcp", "10.0.1.20", dport=51514, sport=443, dst="203.0.113.7")
    print("client 203.0.113.7:51514 → web server 10.0.1.20:443, then the reply 10.0.1.20:443 → client:51514\n")

    sg = SecurityGroup([Rule("accept", "tcp", None, [(443, 443)])])
    print(f"Security group (stateful):  request {'ALLOW' if sg.allows(client) else 'DENY'};"
          "  reply ALLOW automatically (connection tracked)")

    _, https = parse_rules("accept proto tcp dport 443")
    _, eph = parse_rules("accept proto tcp dport 1024-65535")
    bad = Nacl(inbound=[(100, https[0])], outbound=[(100, https[0])])
    good = Nacl(inbound=[(100, https[0])], outbound=[(100, eph[0])])
    for label, nacl in (("NACL v1 (outbound only 443)", bad), ("NACL v2 (outbound 1024-65535)", good)):
        a_in, why_in = nacl.check("in", client)
        a_out, why_out = nacl.check("out", reply)
        print(f"{label:32} request {a_in.upper()} ({why_in});  reply {a_out.upper()} ({why_out})")

    fw = HostFirewall(*parse_rules("policy drop\naccept state established\naccept proto tcp dport 22"))
    out = Packet("tcp", "10.0.1.20", dport=443, sport=40000, dst="93.184.215.14")
    back = Packet("tcp", "93.184.215.14", dport=40000, sport=443, dst="10.0.1.20")
    print("\nHost firewall (policy drop, accept established, accept 22):")
    print(f"  unsolicited 93.184.215.14:443 → :40000  {fw.inbound(back)[0].upper():6} ({fw.inbound(back)[1]})")
    fw.outbound(out)
    print(f"  after our outbound connection        {fw.inbound(back)[0].upper():6} ({fw.inbound(back)[1]})")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Firewall rule simulator and auditor.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("rules", type=Path)
    e.add_argument("--proto", default="tcp")
    e.add_argument("--src", required=True)
    e.add_argument("--dport", type=int, default=0)
    e.add_argument("--state", default="new", choices=("new", "established"))
    a = sub.add_parser("audit")
    a.add_argument("rules", type=Path)
    sub.add_parser("demo")
    args = ap.parse_args(argv)
    if args.cmd == "demo":
        return demo()
    try:
        policy, rules = parse_rules(args.rules.read_text(encoding="utf-8"))
        if args.cmd == "eval":
            fw = HostFirewall(policy, rules)
            p = Packet(args.proto, args.src, args.dport, sport=50000)
            if args.state == "established":
                fw.outbound(Packet(p.proto, p.dst, p.sport, p.dport, p.src))
            action, why = fw.inbound(p)
            print(f"{action.upper()}  by {why}")
            return 0 if action == "accept" else 1
        findings = audit(policy, rules)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for f in findings:
        print(f"- {f}")
    print(f"{len(rules)} rules, policy {policy}, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
