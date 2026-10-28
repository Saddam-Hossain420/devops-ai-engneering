#!/usr/bin/env bash
# netns_lab.sh — দুটি network namespace (red, blue) একটি Linux bridge-এ, ঠিক Docker-এর default bridge-এর মতো।
#
#   sudo ./netns_lab.sh up   --yes-i-am-in-a-vm          # namespace, veth, bridge তৈরি
#   sudo ./netns_lab.sh up   --nat --yes-i-am-in-a-vm    # + internet access (ip_forward + masquerade)
#   sudo ./netns_lab.sh test --yes-i-am-in-a-vm          # ping ও route যাচাই
#   sudo ./netns_lab.sh down --yes-i-am-in-a-vm          # সব মুছে আগের অবস্থায়
#
# ⚠️ শুধু lab VM-এ। Host-এর network state বদলায় (bridge, namespace; --nat দিলে ip_forward ও nftables table)।
# সব object-এর নাম "lab" দিয়ে চিহ্নিত, এবং down শুধু এই lab-এর তৈরি জিনিস মোছে।
set -euo pipefail

BR=br-lab
SUBNET_PREFIX=10.200.0
NAMESPACES=(red blue)
STATE=/run/netns-lab.ip_forward     # --nat-এর আগের ip_forward মান

usage() { echo "usage: sudo $0 up|test|down [--nat] --yes-i-am-in-a-vm" >&2; exit 2; }

ACTION=${1:-}
shift || true
NAT=0
CONFIRMED=0
for arg in "$@"; do
  case $arg in
    --nat) NAT=1 ;;
    --yes-i-am-in-a-vm) CONFIRMED=1 ;;
    *) usage ;;
  esac
done
[[ $ACTION =~ ^(up|test|down)$ ]] || usage
if [[ $CONFIRMED -ne 1 ]]; then
  echo "refusing: this changes host networking. Re-run inside a lab VM with --yes-i-am-in-a-vm" >&2
  exit 2
fi
if [[ $(id -u) -ne 0 ]]; then
  echo "needs root (sudo)" >&2
  exit 2
fi
command -v ip >/dev/null || { echo "iproute2 'ip' not found" >&2; exit 2; }

up() {
  ip link add "$BR" type bridge
  ip addr add "$SUBNET_PREFIX.1/24" dev "$BR"
  ip link set "$BR" up
  local n=2
  for ns in "${NAMESPACES[@]}"; do
    ip netns add "$ns"
    # veth pair: এক প্রান্ত (veth-red) host-এ bridge-এ, অপর প্রান্ত namespace-এর ভেতরে eth0 নামে
    ip link add "veth-$ns" type veth peer name eth0 netns "$ns"
    ip link set "veth-$ns" master "$BR" up
    ip -n "$ns" link set lo up
    ip -n "$ns" addr add "$SUBNET_PREFIX.$n/24" dev eth0
    ip -n "$ns" link set eth0 up
    ip -n "$ns" route add default via "$SUBNET_PREFIX.1"
    echo "namespace $ns: $SUBNET_PREFIX.$n via veth-$ns on $BR"
    n=$((n + 1))
  done
  if [[ $NAT -eq 1 ]]; then
    sysctl -n net.ipv4.ip_forward > "$STATE"
    sysctl -qw net.ipv4.ip_forward=1
    nft add table ip netns_lab
    nft add chain ip netns_lab postrouting '{ type nat hook postrouting priority srcnat; }'
    nft add rule ip netns_lab postrouting ip saddr "$SUBNET_PREFIX.0/24" oifname != "$BR" masquerade
    echo "NAT enabled (previous ip_forward saved in $STATE)"
  fi
}

check() { # check <description> <command...>
  local desc=$1; shift
  if "$@" >/dev/null 2>&1; then echo "PASS  $desc"; else echo "FAIL  $desc"; FAILED=1; fi
}

test_lab() {
  FAILED=0
  check "red → bridge gateway ($SUBNET_PREFIX.1)" ip netns exec red ping -c1 -W1 "$SUBNET_PREFIX.1"
  check "red → blue ($SUBNET_PREFIX.3) across the bridge" ip netns exec red ping -c1 -W1 "$SUBNET_PREFIX.3"
  check "blue → red ($SUBNET_PREFIX.2)" ip netns exec blue ping -c1 -W1 "$SUBNET_PREFIX.2"
  check "red has its own routing table (default via .1)" \
    bash -c "ip -n red route | grep -q 'default via $SUBNET_PREFIX.1'"
  check "veth-red is a member of $BR" bash -c "ip link show veth-red | grep -q 'master $BR'"
  check "eth0 exists inside red" ip -n red link show eth0
  check "host namespace does not own red's address" bash -c "! ip -o addr | grep -q ' $SUBNET_PREFIX.2/'"
  if [[ -f $STATE ]]; then
    check "red → internet (1.1.1.1) through NAT" ip netns exec red ping -c1 -W2 1.1.1.1
  fi
  return $FAILED
}

down() {
  for ns in "${NAMESPACES[@]}"; do
    ip netns del "$ns" 2>/dev/null && echo "deleted namespace $ns (its veth pair goes with it)" || true
  done
  ip link del "$BR" 2>/dev/null && echo "deleted bridge $BR" || true
  if nft list table ip netns_lab >/dev/null 2>&1; then
    nft delete table ip netns_lab && echo "deleted nftables table netns_lab"
  fi
  if [[ -f $STATE ]]; then
    sysctl -qw net.ipv4.ip_forward="$(cat "$STATE")" && rm -f "$STATE"
    echo "restored net.ipv4.ip_forward"
  fi
}

case $ACTION in
  up) up ;;
  test) test_lab ;;
  down) down ;;
esac
