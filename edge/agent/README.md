# DHCP Agent

Placeholder for the future unprivileged Raspberry Pi `dhcp-agent`.

Planned responsibilities:

- run under `systemd` as a non-root service;
- connect outbound to the device gateway;
- authenticate as an enrolled device;
- send heartbeats;
- download signed config artifacts;
- verify hashes, signatures, target site/device, and versions;
- stage artifacts under a fixed local state directory;
- request local application from the apply helper;
- report deployment results and lease observations.

The agent must not expose an inbound management API.
