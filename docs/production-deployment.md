# RecallNext production deployment

This deployment keeps Exasol Personal private and publishes only the RecallNext
HTTP application through an HTTPS edge. Use either Caddy with a DNS hostname or
Tailscale Funnel. The application remains bound to `127.0.0.1:8080` in both
configurations.

## Runtime boundary

- `exasol-nano` listens on the host for encrypted PyExasol traffic.
- Both containers join the private `recallnext-internal` Docker network. Exasol
  has no published host port, while RecallNext publishes only
  `127.0.0.1:8080`.
- Caddy or Tailscale Funnel publishes that loopback service through HTTPS.
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

## Public HTTPS with Caddy

Point a DNS hostname at the host's public IP. For a short-lived evaluation
deployment without purchasing a domain, `nip.io` can derive a hostname from an
IPv4 address. For example, public IP `203.0.113.10` can use
`recallnext.203-0-113-10.nip.io`. The hostname remains valid only while that
public IP remains assigned to the host.

Allow inbound TCP ports 80 and 443 to the host, set the hostname at runtime, and
start the application plus the hardened Caddy edge:

```bash
export RECALLNEXT_PUBLIC_HOST="recallnext.203-0-113-10.nip.io"
docker compose -f compose.production.yaml -f compose.caddy.yaml up -d --build
docker compose -f compose.production.yaml -f compose.caddy.yaml ps
curl --fail --silent "https://${RECALLNEXT_PUBLIC_HOST}/api/health"
```

Port 80 is used for certificate issuance and HTTP-to-HTTPS redirects. Caddy
stores certificates in a named volume, runs with only `NET_BIND_SERVICE`, has a
read-only root filesystem, and proxies solely to the loopback application.

## Stable free HTTPS with Tailscale Funnel

Install Tailscale from its official Linux repository, enroll the host in a free
personal tailnet, then configure a stable hostname and Funnel:

```bash
sudo tailscale set --hostname=recallnext
sudo tailscale up
sudo tailscale funnel --bg http://127.0.0.1:8080
tailscale funnel status
export RECALLNEXT_PUBLIC_HOST="recallnext.<tailnet>.ts.net"
```

The first `tailscale up` prints a one-time account authorization link. After the
account enables MagicDNS, HTTPS, and Funnel, the status command reports the exact
stable public URL. Replace `<tailnet>` in the exported hostname with the value in
that URL before running the shared verification commands below. Funnel traffic
is outbound from the VM, so ports 80 and 443 do not need to be opened in the EC2
security group.

## Secret rotation

Update `/etc/recallnext/recallnext.env`, then recreate only the application:

```bash
docker compose -f compose.production.yaml up -d --force-recreate recallnext
```

Do not place either secret in a URL, browser bundle, image layer, GitHub issue,
or committed `.env` file.

## Verification

```bash
curl --fail --silent "https://${RECALLNEXT_PUBLIC_HOST}/api/health"
curl --fail --silent "https://${RECALLNEXT_PUBLIC_HOST}/api/incidents"
docker inspect --format '{{json .State.Health}}' recallnext-recallnext-1
docker compose -f compose.production.yaml logs --tail=100 recallnext
```

For a protected request, provide `Authorization: Bearer <reviewer-token>`. A live
document extraction returns a proposed fact and `requires_human_review: true`; it
does not create evidence or alter any decision until the separate save and accept
steps complete.
