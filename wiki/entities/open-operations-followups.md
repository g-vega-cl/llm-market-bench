---
tags: [operations, infrastructure, deploy, cloudflare, failover, credentials]
category: entity
---

# Open operations follow-ups

The infrastructure work that is **not** automatable by an agent: steps that need a password, a
console, or an owner decision. Everything here is pending; completed items are deleted, not struck
through (see [[SCHEMA]]). The self-hosted front door itself is described in
[[entities/self-hosted-web-deployment]]; the replica topology in [[entities/secondary-minipc-edge]].

## Blocked on credentials or console

### 1. MiniPC sudo password is unknown

`cv-minipc` is the only human account on the MiniPC (uid 1000, member of `sudo`), and its sudo
password is not the one recorded in the local password note — three attempts fail. SSH works (key +
Tailscale), so work that does not need root is unaffected, but any package or unit change is blocked.

Recovery, from a hypervisor console (not SSH):

```bash
# GRUB: press e, append to the linux line, boot with Ctrl-X
rw init=/bin/bash
passwd cv-minipc
exec /sbin/init
```

Alternative if the hypervisor offers a root shell (Proxmox): `qm terminal` / `pct enter`, then
`passwd cv-minipc`.

### 2. Rotate the credentials that were pasted into a chat transcript

The MiniPC sudo password and the second value in the same note were written in plain text into a chat
log. Both must be replaced rather than reused. Store the replacements in a password manager, and
prefer key-based access so the sudo password is only needed for `visudo`-level changes.

### 3. cloudflared 2026.11.2 on the MiniPC

Fedora runs 2026.11.2; the MiniPC still runs 2026.10.4. The `.deb` is staged at
`/tmp/cloudflared.deb` on the MiniPC (version 2026.11.2, amd64), but `/tmp` does not survive a reboot —
re-download if it is gone:

```bash
curl -fsSL -o /tmp/cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i /tmp/cloudflared.deb && sudo systemctl restart cloudflared
cloudflared --version && rm -f /tmp/cloudflared.deb
```

Restart one host at a time: two connectors serve the tunnel, so the site stays up. After each host,
confirm `journalctl -u cloudflared | grep "Registered tunnel connection"` shows four connections and
that `https://www.benchify.dev/` still answers 200.

### 4. Tailscale SSH check-mode can lapse

`ssh cv-minipc@minipc` intermittently demands web re-authentication ("Tailscale SSH requires an
additional check"). While that check is pending, every SSH step of `docker/archive/deploy_secondary.sh`
blocks — the auto-deploy watcher stalls on its MiniPC step and looks like a deploy failure. Either
complete the check when prompted, or switch that node to non-interactive SSH ACLs (`tailscale up
--ssh`) so maintenance is not gated on a browser.

## Owner decisions

### 5. `/strata/` returns 502 on the archive proxy

`docker/archive/nginx.conf` routes `location /strata/` to `http://172.17.0.1:8080/`, and nothing
listens on that port, so the route answers 502. It is unrelated to the proxy-rebind work, but it
masks genuine upstream errors. Decide: restore the Strata service behind that port, or delete the
location block so a missing upstream is visible as a 404 rather than a fake gateway error.

### 6. Failover is incomplete for Strata

Two gaps make a MiniPC promotion partially non-functional:

- `docker/archive/nginx.secondary.conf` has **no** `/strata/` location, so after a promotion
  `/strata/*` falls into `location /` (PostgREST) and 404s.
- `docker/archive/docker-compose.secondary.yml` hardcodes
  `STRATA_BASE_URL=http://primary-workstation:3001/strata/v1` for `free-llm-proxy`,
  `live-spy-trader` and `recipe-worker`, so those workers keep calling the dead workstation.

Decide between running Strata locally on the MiniPC and documenting `/strata` as unavailable during
failover.

### 7. No replication-lag gate before promotion

`docker/archive/promote_to_primary.sh` promotes without checking `pg_stat_wal_receiver` /
`pg_stat_replication`. A standby that has stopped streaming or is minutes behind would be promoted
silently, discarding the unreplayed WAL window. Add a gate that refuses to promote when the receiver
is not `streaming` or when replay lags beyond a threshold.

### 8. Deployer-level locking

The rebind helper takes a per-host `flock`, so two overlapping rebinds cannot validate each other's
bytes. `deploy_web.sh`, `deploy_secondary.sh` and `promote_to_primary.sh` themselves take no lock, so
two full deploys can still interleave builds and restarts. Add the same lock at deployer entry.

### 9. Mount-source flip on byte-identical configs

The rebind assertion compares bytes, not `Mounts[].Source`. Fedora's `web-proxy` mounts
`~/.local/share/benchify-deploy-repo/docker/archive/nginx.web.conf` while `deploy_web.sh` passes the
repo checkout's path; both files are byte-identical today, so a rebuild silently re-points the mount
and the next deploy re-points it back — churn the guard cannot see. Either assert the mount source
equals the validated path, or make every caller pass the path that is actually mounted.

### 10. `promote_to_primary.sh` has no host guard

Run from the workstation it would rewrite the local `nginx.secondary.conf` and write a local
`.promoted` while the MiniPC stays unguarded. A check that the MiniPC containers exist on the current
host would make the mistake impossible instead of merely documented.

## Housekeeping

- Review and either commit or discard the seven files that another session left dirty in
  `apps/engine/recipes/`, `apps/free_llm_proxy/` and `apps/web/src/features/recipes/builder/`.
- `wiki/concepts/code-hotspots.md` is regenerated by `verify.sh --write-wiki` and lands in unrelated
  commits; excluding it from feature commits keeps diffs honest.

## Related

- [[entities/self-hosted-web-deployment]] — the proxy, deployer, and rebind guard these items touch
- [[entities/secondary-minipc-edge]] — replica topology, promotion and demotion procedure
- [[concepts/hybrid-database-archival]] — primary/archive database split
