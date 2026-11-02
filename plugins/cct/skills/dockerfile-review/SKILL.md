---
name: dockerfile-review
description: Reviews a Dockerfile (and its .dockerignore and build workflow) for container hardening — non-root user, multi-stage, digest-pinned bases, secrets baked into layers, build-arg credential leaks. Use when the user says "review this Dockerfile", "harden this image", "docker security review", "is this image safe", "check my container build", or asks about image hardening, base images, or secrets in images. Also use before adopting a new service's image into a cluster.
user_invocable: true
context: fork
model: sonnet
effort: high
background: false
---

# Review a Dockerfile

Container images are **distribution artifacts**: whatever lands in a layer is pushed to a
registry and pullable forever. A leaked `.env`, a build-time token, a compiler an attacker can
pivot with. The whole game is to make the runtime image contain as little as possible, run it as
nobody, and make it reproducible.

Every check below fired on a real OMR image in the 2026-08-11 audit. This is not a generic
checklist.

## How to run the review

Read **all three** — a Dockerfile alone hides half the findings:

1. the `Dockerfile`
2. the `.dockerignore` (especially its `!` re-include lines)
3. the **build workflow** (`.github/workflows/*`) — how secrets reach the build

Then work the table. Report findings as `file:line`, severity, and the concrete fix.

## The checks

### 1. Non-root — `USER` is present (CRITICAL)

```bash
grep -n '^USER' Dockerfile || echo "NO USER — runs as uid 0"
```

No `USER` means uid 0. A breached root container is one kernel bug from root on the node. In the
audit **4 of 4** audited images had no `USER`.

- Prefer a **numeric** uid (`USER 10001`). `runAsNonRoot: true` is checked by the kubelet against
  the image's configured user, and a non-numeric user can be rejected at admission.
- Distroless: `USER nonroot` (uid 65532) is fine — it resolves numerically.
- The `USER` must be in the **final** stage. A `USER` in a build stage does nothing.

### 2. No credentials in `ENV` or `ARG` (CRITICAL)

```bash
grep -nEi '^(ENV|ARG).*(TOKEN|SECRET|PASSWORD|KEY|CREDENTIAL|_PRO=|_COM=|AUTH)' Dockerfile
```

`ENV` in **any** stage the final image inherits from is readable via `docker inspect` and from
any shell in the container. Real finding: two vendor licence credentials hardcoded in a `base`
stage that `production` was `FROM`.

**Build-time secrets must use `--mount=type=secret`, never `ARG`.** A build arg is recoverable
from build history, and if the workflow sets `cache-to: type=gha,mode=max` the consuming layer
is exported into the GitHub Actions cache. Check the workflow for the asymmetry — one real case
passed the *same* PAT correctly as a secret for `npm_token` and incorrectly as a `build-arg` for
the rubygems token, in one file.

### 3. `.dockerignore` — read the `!` lines (HIGH)

```bash
grep -n '^!' .dockerignore
```

A `.*` rule followed by `!/.gcp-keyfile.json` and `!/.htpasswd` **deliberately bakes those in**.
Even if the file is absent today, the allow-list entry is a loaded gun for the moment a file with
that name appears. Also confirm `.env*`, `.git`, and key material are excluded.

### 4. Multi-stage — no build toolchain in the runtime (HIGH)

The runtime stage holds only the app + runtime libs. A `COPY . /app` into the final stage ships
`.git`, source, and whatever the context contains. Compilers, `apt`, `npm`, `git` in a runtime
image are pivot surface.

### 5. Base pinned by digest (MEDIUM)

```bash
grep -nE '^FROM' Dockerfile | grep -v '@sha256:'
```

`:stable`, `:latest`, or a bare tag means the image you audited is not the image that shipped.
Pin `FROM …@sha256:…`. Resolve a digest without pulling:

```bash
curl -sSL -D- -o/dev/null \
  -H "Accept: application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json" \
  "https://<registry>/v2/<repo>/manifests/<tag>" | grep -i docker-content-digest
```

### 6. Frozen lockfile installs (MEDIUM)

`npm ci`, `uv sync --frozen`, `bundle install --deployment`. An unfrozen install resolves fresh
versions at build time — non-reproducible, and an opening for dependency confusion.

### 7. No dev/test deps in runtime (LOW)

`NODE_ENV=production`, `--no-dev`, `BUNDLE_WITHOUT=development:test`.

### 8. Read-only-rootfs friendly (LOW)

Nothing writes to the image filesystem at runtime; scratch goes to `/tmp`. This is what lets the
pod set `readOnlyRootFilesystem: true`. If the app must write, mount a volume — never drop the
control.

### 9. Scanning exists at all

`trivy image --severity HIGH,CRITICAL --ignore-unfixed <image>` plus a secret scanner (gitleaks)
in CI. In the audit, the one repo carrying the Critical finding was also the only one with
**neither**. Check for both, per repo — "most repos have it" is not a control.

## Pairing with Kubernetes

An image hardened here still needs the pod to assert it. Report the `securityContext` that
matches, and use the `k8s-workloads-audit` skill for the runtime half:

```yaml
securityContext:
  runAsNonRoot: true
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities: { drop: ["ALL"] }
  seccompProfile: { type: RuntimeDefault }
```

## Output format

A table of findings ordered by severity, each with `file:line`, what breaks, and the fix. Then a
**controls-met count** so it is countable. Phrase every row so **✓ = good** — a table mixing
"has USER ✗" with "has creds in ENV ✓" is unreadable and will be misread in a deck.

## Do not

- Report "no `USER`" as low severity. It is the control that decides whether an app compromise
  becomes a node compromise.
- Suggest `docker scan`/`docker scout` as the fix for a baked secret. Rotation is the only
  remedy — a leaked layer leaks it permanently. Say so explicitly.
