### Network Neighborhood:

```
arp -na
```

```
echo -e 192.168.1.{1..254}"\n" |nslookup |grep name
```

alternatively use nmap:

```
sudo nmap -sn 192.168.0.0/24
```

Only return the IP-addresses:

```
sudo nmap -sn 192.168.0.0/24 | grep report | awk '{ print $5 }'
```

### Ping
As a troubleshooting tool, ping is invaluable. The option in Network Utility 
helped to diagnose numerous connectivity issues and, fortunately, Terminal 
replicates the feature well.

```
ping <hostname>
```

```
ping <ip-address>
```

### Lookup 
The Lookup tool in Network Utility allowed you to identify the IP addresses 
associated with a domain name and vice versa. In Terminal, the nslookup 
command effectively replicates this feature.

```
nslookup <hostname>
```

```
nslookup <ip-address>
```

or

```
dig <hostname>
```

```
dig <ip-address>
```

### Traceroute
Traceroute was another useful Network Utility troubleshooting tool, a
nd Terminal won’t leave you disappointed with its version. The feature works 
similarly to ping but allows you to track where packets go, where they stop, 
and where they stall. With this knowledge, you can identify problem areas 
within your network.

```
traceroute apple.com
```

### Whois
The Whois tool in Network Utility allowed you to find information about a 
domain name owner. Terminal replicates this feature with the whois command

```
whois apple.com
```

### Finger
Finger in Network Utility provided information about users on your network, 
and a simple Terminal command can do the same. The tool, however, is only 
useful for retrieving local data and won’t achieve much outside of your own network.

```
finger juergen
```

```
finger user@host
```

### Port Scan
Network Utility’s Port Scan was a functional and intuitive tool for identifying 
open ports on your network. The feature is useful for troubleshooting any issues 
that involve the use of specific ports. For example, if you’re unable to send mail, 
ensuring the correct port is open may be necessary.

In Terminal, the nc netcat command helps replicate this feature. To make the input 
work as intended, you should also add -z and -v flags. The first flag, -z, prompts 
Terminal to scan for open ports, and the second, -v, enables verbose mode.

```
nc -vz 192.168.0.1 1-1000
```

or

```
nc -z 192.168.0.1 1-1000
```
