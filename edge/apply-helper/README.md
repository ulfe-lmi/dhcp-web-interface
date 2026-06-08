# DHCP Apply Helper

Placeholder only.

The future `dhcp-apply-helper` is the tiny privileged local component that applies already-validated staged artifacts to `dnsmasq`.

Required future constraints:

- local-only;
- no network listener;
- no arbitrary commands;
- no arbitrary service names;
- no arbitrary file paths;
- writes only managed `dnsmasq` files;
- validates candidates with `dnsmasq --test`;
- applies atomically;
- rolls back to the previous known-good config on failure.

Expected managed path:

```text
/etc/dnsmasq.d/managed/
```

No real apply logic is implemented in this scaffold.
