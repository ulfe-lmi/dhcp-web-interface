# Device Gateway

Placeholder for the future Go device gateway.

Planned responsibilities:

- accept outbound edge appliance connections;
- authenticate device identity;
- maintain connection registry;
- send config availability notifications;
- accept heartbeats, deployment results, and lease reports;
- forward events to the backend or an internal API.

The gateway must not own business authorization or IPAM validation.
