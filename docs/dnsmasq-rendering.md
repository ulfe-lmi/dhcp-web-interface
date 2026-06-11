# dnsmasq Rendering

The backend can create private config versions that render structured DHCP/IPAM data into deterministic `dnsmasq` preview files. This is not a deployment system yet.

Generated files:

- `dnsmasq/10-ranges.conf`
- `dnsmasq/20-options.conf`
- `dnsmasq/30-reservations.conf`
- `dnsmasq/40-hosts.conf`

Rendering rules:

- each file starts with a generated header and no timestamp;
- subnets sort by CIDR;
- pools sort by start IP, end IP, and name;
- reservations sort by IP address, MAC address, and hostname;
- disabled pools and disabled reservations are skipped;
- subnet tags are derived from CIDR, such as `subnet-192-168-10-0-24`;
- DNS server order follows the stored subnet `dns_servers` list.

Current directives:

- enabled pools render as `dhcp-range` lines;
- subnet gateway and DNS servers render as common `dhcp-option` lines;
- enabled reservations render as `dhcp-host` lines with infinite static leases;
- enabled reservation hostnames render as hostname-only `address=/hostname/ip` records.

Current limitations:

- no FQDN/domain model or aliases yet;
- no arbitrary raw DHCP options;
- no real artifact signing;
- no `dnsmasq --test` invocation;
- no file writes, gateway notification, deployment record, or Raspberry Pi apply logic.
