#!/bin/bash
ip link add mvl-brg link eth0 type macvlan mode bridge
ip addr add 192.168.0.63/32 dev mvl-brg
ip link set mvl-brg up
ip route add 192.168.0.32/27 dev mvl-brg
