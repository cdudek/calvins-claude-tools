#!/usr/bin/env bash
# Usage: pr-context.sh <pr_number>
# Dumps PR metadata, commits, body, linked issues, and reviews for AI parsing.
# Output: sections delimited per the -#-#- convention (see CLAUDE.md).
# Sections:
#   -#-#- PR -#-#-                          (key-value; includes owner_repo for caller convenience)
#   -#-#- COMMITS -#-#-                     (repeating commits, each ended by -#-#- END COMMIT -#-#-)
#   -#-#- BEGIN PR_BODY -#-#- ... -#-#- END PR_BODY -#-#-
#   -#-#- LINKED_ISSUES -#-#-               (key-value; linear ids filtered against a common-acronym stoplist)
#   -#-#- REVIEWS -#-#-                     (key-value rows, one per reviewer)
set -euo pipefail

PR="${1:?Usage: pr-context.sh <pr_number>}"

OWNER_REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner')
META=$(gh pr view "$PR" --json number,title,state,author,baseRefName,headRefName,additions,deletions,changedFiles,body,labels,commits)

echo "-#-#- PR -#-#-"
echo "- number: $(echo "$META" | jq -r '.number')"
echo "- owner_repo: $OWNER_REPO"
echo "- title: $(echo "$META" | jq -r '.title')"
echo "- state: $(echo "$META" | jq -r '.state')"
echo "- author: $(echo "$META" | jq -r '.author.login')"
echo "- base: $(echo "$META" | jq -r '.baseRefName')"
echo "- head: $(echo "$META" | jq -r '.headRefName')"
echo "- additions: $(echo "$META" | jq -r '.additions')"
echo "- deletions: $(echo "$META" | jq -r '.deletions')"
echo "- changed_files: $(echo "$META" | jq -r '.changedFiles')"
echo "- labels: $(echo "$META" | jq -r '[.labels[].name] | join(",")')"

echo ""
echo "-#-#- COMMITS -#-#-"
echo "$META" | jq -r '.commits[] | "### \(.oid)\nsubject: \(.messageHeadline)\nauthor: \(if (.authors | length) > 0 and .authors[0].name then "\(.authors[0].name) <\(.authors[0].email)>" else "unknown" end)\nbody:\n\(.messageBody)\n-#-#- END COMMIT -#-#-"'

echo ""
echo "-#-#- BEGIN PR_BODY -#-#-"
echo "$META" | jq -r '.body // ""'
echo "-#-#- END PR_BODY -#-#-"

echo ""
echo "-#-#- LINKED_ISSUES -#-#-"
# Filter Linear-id candidates against common acronyms that share the
# UPPER-N pattern (HTTP-2, UTF-8, OAUTH-1, WCAG-2, etc) so Phase 2 of
# `squash pr` doesn't spam Linear MCP with garbage IDs. The stoplist
# matches the prefix only (the part before the dash). Any prefix not on
# the list is forwarded; Linear MCP is expected to handle "not found"
# gracefully.
SEARCH=$(echo "$META" | jq -r '.title + " " + (.body // "")')
LINEAR=$(echo "$SEARCH" | grep -oE '[A-Z]+-[0-9]+' | sort -u | awk -F- '
  BEGIN {
    split("HTTP HTTPS HTTP1 HTTP2 HTTP3 UTF UCS ASCII OAUTH RFC ISO IEC TLS SSL API SDK CLI CSS HTML JSON XML YAML TOML UUID GUID IPV IPV4 IPV6 MAC DNS TCP UDP WCAG ARIA AWS GCP GCE GKE JWT JWE JWA JWK SHA SHA1 SHA256 SHA512 MD MD5 AES RSA HMAC PBKDF BCRYPT SCRYPT BASE UTC GMT PST EST CET PDT EDT IST CEST UV UID GID PID TTY HID USB SDD HDD RAM ROM CPU GPU TPU NPU VPN VLAN LAN WAN MAN PAN VRF MPLS BGP OSPF RIP ICMP IGMP ARP RARP NDP DHCP NTP NFS SMB CIFS SCP SFTP FTP FTPS IMAP POP SMTP MIME SASL GSSAPI LDAP RADIUS SAML OIDC FIDO TOTP HOTP PAP CHAP EAP WPA WEP TKIP CCMP GCM CCM EAX OCB", k, " ")
    for (i in k) stop[k[i]] = 1
  }
  !($1 in stop) { print $0 }
' || true)
GITHUB=$(echo "$SEARCH" | grep -oE '#[0-9]+' | sort -u || true)
LINEAR_OUT=$(echo "$LINEAR" | paste -sd, -)
GITHUB_OUT=$(echo "$GITHUB" | paste -sd, -)
echo "- linear: ${LINEAR_OUT:-none}"
echo "- github: ${GITHUB_OUT:-none}"

echo ""
echo "-#-#- REVIEWS -#-#-"
REVIEWS_OUT=$(gh api "repos/{owner}/{repo}/pulls/$PR/reviews" --jq '.[] | "- \(.user.login): \(.state)"' 2>/dev/null || true)
echo "${REVIEWS_OUT:-- none}"
