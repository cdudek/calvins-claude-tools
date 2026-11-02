#!/bin/sh
# Your own development database `<firstname_lastname>_dev` on the Cloud SQL instance
# heydiff. Run through make (README.md, "Development database"):
#   make dev-db        register (first run) or connect, write .env.local, migrate
#   make dev-db-proxy  start the Cloud SQL Auth Proxy only
#   make dev-db-stop   stop it
#   make dev-db-psql   psql into your database
# `sh scripts/dev-db.sh name "Full Name"` prints the derived name (tested in tests/).
#
# Access is granted in pokbytes/terraform-infra: terraform/developers.json maps
# firstname-lastname to a Google account. You can reach your own database and no other.
# No password and no token is ever written or printed: the proxy logs in with your
# Application Default Credentials (IAM database auth).
set -eu

INSTANCE="heydiff:europe-west1:heydiff-db-shared"
TF_REPO="${TF_REPO:-pokbytes/terraform-infra}"
PORT="${DEV_DB_PORT:-5432}"
STATE_DIR=".dev-db"
PIDFILE="$STATE_DIR/proxy.pid"
PORTFILE="$STATE_DIR/proxy.port"
LOG="$STATE_DIR/proxy.log"
export CLOUDSDK_ACTIVE_CONFIG_NAME="${CLOUDSDK_ACTIVE_CONFIG_NAME:-heydiff}"

die() {
  printf 'dev-db: %s\n' "$*" >&2
  exit 1
}

need() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is not installed. $2"
}

# "Calvin Dudek" -> calvin-dudek. German umlauts become ae/oe/ue/ss, other accents are
# dropped, anything that is not a-z becomes one hyphen. Node, not iconv: iconv's
# transliteration differs between macOS and glibc.
derive_name() {
  node -e '
    const s = process.argv[1].normalize("NFC")
      .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue")
      .replace(/Ä/g, "Ae").replace(/Ö/g, "Oe").replace(/Ü/g, "Ue").replace(/ß/g, "ss")
      .normalize("NFKD").replace(/[̀-ͯ]/g, "")
      .toLowerCase().replace(/[^a-z]+/g, "-").replace(/^-+|-+$/g, "");
    process.stdout.write(s);
  ' "$1"
}

resolve_name() {
  raw="${NAME:-$(git config user.name 2>/dev/null || true)}"
  [ -n "$raw" ] || die "no name: set git config user.name, or run make dev-db NAME=firstname-lastname"
  DEV_NAME="$(derive_name "$raw")"
  # Same rule as terraform-infra's foundation precondition.
  printf '%s' "$DEV_NAME" | grep -Eq '^[a-z]+(-[a-z]+)*$' ||
    die "\"$raw\" does not give a firstname-lastname name; run make dev-db NAME=firstname-lastname"
  DATABASE="$(printf '%s' "$DEV_NAME" | tr - _)_dev" # terraform-infra README "Naming": the environment last
}

resolve_account() {
  need gcloud "Install: brew install --cask google-cloud-sdk (Linux: https://cloud.google.com/sdk/docs/install)"
  if ! gcloud config configurations describe "$CLOUDSDK_ACTIVE_CONFIG_NAME" >/dev/null 2>&1; then
    die "gcloud configuration \"$CLOUDSDK_ACTIVE_CONFIG_NAME\" does not exist. Create it once (your default configuration stays active):
  gcloud config configurations create $CLOUDSDK_ACTIVE_CONFIG_NAME --no-activate
  CLOUDSDK_ACTIVE_CONFIG_NAME=$CLOUDSDK_ACTIVE_CONFIG_NAME gcloud auth login
  CLOUDSDK_ACTIVE_CONFIG_NAME=$CLOUDSDK_ACTIVE_CONFIG_NAME gcloud config set project heydiff"
  fi
  ACCOUNT="$(gcloud config get-value account 2>/dev/null || true)"
  printf '%s' "$ACCOUNT" | grep -Eq '^[^@[:space:]]+@[^@[:space:]]+$' ||
    die "no account in gcloud configuration \"$CLOUDSDK_ACTIVE_CONFIG_NAME\". Run: CLOUDSDK_ACTIVE_CONFIG_NAME=$CLOUDSDK_ACTIVE_CONFIG_NAME gcloud auth login"
}

proxy_running() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

start_proxy() {
  need cloud-sql-proxy "Install: brew install cloud-sql-proxy (Linux: https://cloud.google.com/sql/docs/postgres/sql-proxy#install)"
  if proxy_running; then
    PORT="$(cat "$PORTFILE")"
    echo "dev-db: proxy already running on 127.0.0.1:$PORT (pid $(cat "$PIDFILE"))"
    return 0
  fi
  # --auto-iam-authn takes Application Default Credentials; the proxy refuses --gcloud-auth with it.
  [ -n "${ACCOUNT:-}" ] || resolve_account
  gcloud auth application-default print-access-token >/dev/null 2>&1 ||
    die "no Application Default Credentials. Run once: gcloud auth application-default login --account $ACCOUNT"
  mkdir -p "$STATE_DIR"
  nohup cloud-sql-proxy --auto-iam-authn "$INSTANCE" --port "$PORT" >"$LOG" 2>&1 &
  pid=$!
  echo "$pid" >"$PIDFILE"
  echo "$PORT" >"$PORTFILE"
  i=0
  while [ "$i" -lt 30 ]; do
    if grep -q 'ready for new connections' "$LOG"; then
      echo "dev-db: proxy running on 127.0.0.1:$PORT (pid $pid, log $LOG)"
      return 0
    fi
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$PIDFILE" "$PORTFILE"
      tail -n 5 "$LOG" >&2
      die "the proxy exited (see $LOG). Port $PORT busy? Try: make dev-db DEV_DB_PORT=5433"
    fi
    sleep 1
    i=$((i + 1))
  done
  die "the proxy did not get ready in 30 s (see $LOG)"
}

stop_proxy() {
  if proxy_running; then
    kill "$(cat "$PIDFILE")"
    echo "dev-db: proxy stopped"
  else
    echo "dev-db: no proxy running"
  fi
  rm -f "$PIDFILE" "$PORTFILE"
}

database_url() {
  user="$(node -e 'process.stdout.write(encodeURIComponent(process.argv[1]))' "$ACCOUNT")"
  # A hyphen is legal in a URL path, so the database name needs no escaping here; in SQL
  # it is an identifier that must be double-quoted ("dev-calvin-dudek").
  DATABASE_URL="postgresql://$user@127.0.0.1:$PORT/$DATABASE?sslmode=disable"
}

write_env_local() {
  line="DATABASE_URL=\"$DATABASE_URL\""
  if [ -f .env.local ] && grep -q '^DATABASE_URL=' .env.local; then
    awk -v l="$line" '/^DATABASE_URL=/ { print l; next } { print }' .env.local >.env.local.tmp
    mv -f .env.local.tmp .env.local
  else
    if [ -s .env.local ] && [ -n "$(tail -c 1 .env.local)" ]; then echo >>.env.local; fi
    printf '%s\n' "$line" >>.env.local
  fi
  echo "dev-db: DATABASE_URL for $DATABASE written to .env.local"
}

# Prints the account registered for $DEV_NAME on terraform-infra main, or nothing.
registered_account() {
  json="$(gh api -H 'Accept: application/vnd.github.raw+json' \
    "repos/$TF_REPO/contents/terraform/developers.json?ref=main" 2>/dev/null)" ||
    die "cannot read terraform/developers.json on $TF_REPO main (not merged yet, or no access: gh auth status)"
  printf '%s' "$json" | node -e '
    let s = ""; process.stdin.on("data", (d) => (s += d)).on("end", () => {
      process.stdout.write(JSON.parse(s)[process.argv[1]] ?? "");
    });
  ' "$DEV_NAME"
}

open_registration_pr() {
  branch="dev-db/$DEV_NAME"
  url="$(gh pr list -R "$TF_REPO" --head "$branch" --state open --json url -q '.[0].url')"
  if [ -z "$url" ]; then
    tmp="$(mktemp -d "${TMPDIR:-/tmp}/terraform-infra.XXXXXX")"
    trap 'rm -rf "$tmp"' EXIT
    gh repo clone "$TF_REPO" "$tmp" -- --quiet --depth 1 --branch main
    git -C "$tmp" switch -q -c "$branch"
    node -e '
      const fs = require("fs");
      const [file, key, account] = process.argv.slice(1);
      const o = JSON.parse(fs.readFileSync(file, "utf8"));
      o[key] = account;
      const sorted = Object.fromEntries(Object.keys(o).sort().map((k) => [k, o[k]]));
      fs.writeFileSync(file, JSON.stringify(sorted, null, 2) + "\n");
    ' "$tmp/terraform/developers.json" "$DEV_NAME" "$ACCOUNT"
    git -C "$tmp" commit -q -am "feat(databases): add developer $DEV_NAME"
    git -C "$tmp" push -q -u origin "$branch"
    url="$(cd "$tmp" && gh pr create --base main --head "$branch" \
      --title "feat(databases): add developer $DEV_NAME" \
      --body "Adds \`$DEV_NAME\` ($ACCOUNT) to \`terraform/developers.json\`: an IAM database user, \`cloudsql.client\` + \`cloudsql.instanceUser\`, and the database \`$DATABASE\` owned by that user (README, \"Developer databases\"). Opened by \`make dev-db\` in heydiff-web.")"
  fi
  cat >&2 <<EOF

dev-db: $DEV_NAME is not registered yet. Registration PR:
$url

Once it is merged and the Terraform run on main has finished, run make dev-db again.
EOF
  exit 1
}

cmd_up() {
  need node "Install Node (see .nvmrc)."
  need gh "Install: brew install gh, then gh auth login"
  resolve_name
  resolve_account
  registered="$(registered_account)" || exit 1 # a read error must never open a PR
  [ -n "$registered" ] || open_registration_pr
  [ "$registered" = "$ACCOUNT" ] ||
    die "$DEV_NAME is registered as $registered, but gcloud configuration \"$CLOUDSDK_ACTIVE_CONFIG_NAME\" uses $ACCOUNT. Log in as $registered (CLOUDSDK_ACTIVE_CONFIG_NAME=$CLOUDSDK_ACTIVE_CONFIG_NAME gcloud auth login) or fix the line in $TF_REPO."
  start_proxy
  database_url
  write_env_local
  DATABASE_URL="$DATABASE_URL" npm run db:migrate
}

cmd_psql() {
  need psql "Install: brew install libpq && brew link --force libpq (Linux: apt install postgresql-client)"
  need node "Install Node (see .nvmrc)."
  resolve_name
  resolve_account
  start_proxy
  database_url
  exec psql "$DATABASE_URL"
}

case "${1:-}" in
  up) cmd_up ;;
  proxy) start_proxy ;;
  stop) stop_proxy ;;
  psql) cmd_psql ;;
  name) derive_name "${2:?usage: dev-db.sh name \"Full Name\"}" && echo ;;
  *) die "usage: dev-db.sh up|proxy|stop|psql|name \"Full Name\"" ;;
esac
