# RecallNext production deployment

This deployment keeps Exasol Personal and the RecallNext application private on
the host. Tailscale Funnel is the only public entry point and terminates HTTPS at
a stable `recallnext.<tailnet>.ts.net` address. No AWS inbound web port is needed.

## Runtime boundary

- `exasol-nano` listens on the host for encrypted PyExasol traffic.
- Both containers join the private `recallnext-internal` Docker network. Exasol
  has no published host port, while RecallNext publishes only
  `127.0.0.1:8080`.
- Tailscale Funnel publishes that loopback service through managed HTTPS.
- Read endpoints are public. Every extraction or evidence state change requires
  the runtime reviewer bearer token.
- Authentication defaults on. A missing or short reviewer token stops the API
  instead of exposing write operations.
- The OpenAI key and reviewer token exist only in the root-owned runtime env file.
  They are never compiled into the frontend image or committed to Git.

## Build and start

Create `/etc/recallnext/recallnext.env` from `deploy/recallnext.env.example`, fill
the runtime values, then protect it:

```bash
sudo install -d -m 0700 /etc/recallnext
sudo install -m 0600 deploy/recallnext.env.example /etc/recallnext/recallnext.env
sudoedit /etc/recallnext/recallnext.env
docker network create recallnext-internal
docker network connect recallnext-internal exasol-nano
docker compose -f compose.production.yaml build --pull
docker compose -f compose.production.yaml up -d
docker compose -f compose.production.yaml ps
curl --fail --silent http://127.0.0.1:8080/api/health
```

The Compose service is read-only, drops Linux capabilities, cannot gain new
privileges, has bounded logs, and restarts after a host reboot.

## Stable free HTTPS address

Install Tailscale from its official Linux repository, enroll the host in a free
personal tailnet, then configure a stable hostname and Funnel:

```bash
sudo tailscale set --hostname=recallnext
sudo tailscale up
sudo tailscale funnel --bg http://127.0.0.1:8080
tailscale funnel status
```

The first `tailscale up` prints a one-time account authorization link. After the
account enables MagicDNS, HTTPS, and Funnel, the status command reports the exact
stable public URL. Funnel traffic is outbound from the VM, so ports 80 and 443 do
not need to be opened in the EC2 security group.

## Secret rotation

Update `/etc/recallnext/recallnext.env`, then recreate only the application:

```bash
docker compose -f compose.production.yaml up -d --force-recreate recallnext
```

Do not place either secret in a URL, browser bundle, image layer, GitHub issue,
or committed `.env` file.

## Verification

```bash
curl --fail --silent https://recallnext.<tailnet>.ts.net/api/health
curl --fail --silent https://recallnext.<tailnet>.ts.net/api/incidents
docker inspect --format '{{json .State.Health}}' recallnext-recallnext-1
docker compose -f compose.production.yaml logs --tail=100 recallnext
```

For a protected request, provide `Authorization: Bearer <reviewer-token>`. A live
document extraction returns a proposed fact and `requires_human_review: true`; it
does not create evidence or alter any decision until the separate save and accept
steps complete.
