Update root.key:

```
sudo docker exec unbound unbound-anchor -a /opt/unbound/etc/unbound/root.key
```

Update root.hints

```
wget https://www.internic.net/domain/named.root -O /pfad/zu/unbound/root.hints
```

In unbound.conf Parameter setzen:

```
auto-trust-anchor-file: "/opt/unbound/etc/unbound/root.key"
root-hints: "/opt/unbound/etc/unbound/root.hints"
```

Check

```
dig @192.168.1.39 com. SOA +dnssec
```
