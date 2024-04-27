# vlan.sh
#
# On Synology this file needs to be placed into
# /usr/local/etc/rc.d

#!/bin/sh
# insmod /lib/modules/8021q.ko

# First delete possibly existing VLAN interfaces
ip link del mvlbr.200
ip link del eth0.200

# Set up networking interface on VLAN 200
# Prerequisite: VLAN has to be set up on router or L3 switch
ip link add link eth0 name eth0.200 type vlan id 200
ip addr add 192.168.200.2/24 brd 192.168.200.255 dev eth0.200
# Uncomment the following 2 lines if not using IPv6
ip -6 addr add fd00:0:0:0::10/64 dev eth0
ip -6 addr add fd00:0:0:200::2/64 dev eth0.200
ip link set dev eth0.200 up

# macvlan bridge for communication between host & containers
ip link add mvlbr.200 link eth0.200 type macvlan mode bridge
ip addr add 192.168.200.254/32 dev mvlbr.200
# Uncomment the following line if not using IPv6
ip -6 addr add fd00:0:0:200::fffe/64 dev mvlbr.200
ip link set mvlbr.200 up
ip route del 192.168.200.0/24
ip route add 192.168.200.0/24 dev mvlbr.200
# Uncomment the following 2 lines if not using IPv6
ip -6 route del fd00:0:0:200::/64 dev eth0.200
ip -6 route add fd00:0:0:200::/64 dev mvlbr.200
