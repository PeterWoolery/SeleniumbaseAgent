#!/usr/bin/env bash
# setup.sh — one-command install for SeleniumBase MCP Server
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

log()  { printf "\033[1;34m==>\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m!!\033[0m  %s\n" "$*"; }
ok()   { printf "\033[1;32m✓\033[0m  %s\n" "$*"; }
fail() { printf "\033[1;31m✗\033[0m  %s\n" "$*" >&2; exit 1; }

# ── Prerequisites ─────────────────────────────────────────────────────────────
log "Checking prerequisites"
command -v docker >/dev/null || fail "docker not found. Install Docker Desktop or Docker Engine first."
docker compose version >/dev/null 2>&1 || fail "docker compose plugin not found. Install Docker Compose v2."
ok "docker and docker compose available"

# ── .env ──────────────────────────────────────────────────────────────────────
if [[ -f .env ]]; then
  log ".env already exists — keeping your settings"
else
  log "Creating .env from .env.example"
  cp .env.example .env

  read -r -p "Browser mode [cdp / uc / standard] (default cdp): " mode
  mode="${mode:-cdp}"
  sed -i.bak "s|^BROWSER_MODE=.*|BROWSER_MODE=${mode}|" .env

  read -r -p "Proxy URL (leave blank for none): " proxy_url
  if [[ -n "$proxy_url" ]]; then
    sed -i.bak "s|^SELENIUM_PROXY=.*|SELENIUM_PROXY=${proxy_url}|" .env
    read -r -p "Force proxy on every session? [y/N]: " always
    if [[ "${always,,}" == "y" ]]; then
      sed -i.bak "s|^ALWAYS_PROXY=.*|ALWAYS_PROXY=true|" .env
    fi
  fi

  read -r -p "Host port for MCP SSE (default 8765): " port
  port="${port:-8765}"
  sed -i.bak "s|^MCP_PORT=.*|MCP_PORT=${port}|" .env

  rm -f .env.bak
  ok ".env written"
fi

PORT="$(grep -E '^MCP_PORT=' .env | cut -d= -f2)"
PORT="${PORT:-8765}"

# ── Build + start ─────────────────────────────────────────────────────────────
log "Building container (first run may take 5–10 minutes)"
docker compose build

log "Starting container"
docker compose up -d

log "Waiting for server to be ready…"
for i in {1..30}; do
  if curl -sf --max-time 1 "http://localhost:${PORT}/sse" >/dev/null 2>&1 \
     || curl -s --max-time 1 -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/sse" | grep -qE '^(200|404)$'; then
    ok "server listening on http://localhost:${PORT}/sse"
    break
  fi
  sleep 1
  [[ $i -eq 30 ]] && warn "server didn't respond within 30s — check 'docker compose logs'"
done

# ── Claude Code integration ───────────────────────────────────────────────────
SETTINGS="${HOME}/.claude/settings.json"
SSE_URL="http://localhost:${PORT}/sse"

if [[ -f "$SETTINGS" ]]; then
  read -r -p "Add 'seleniumbase' MCP server to ${SETTINGS}? [Y/n]: " add_cc
  add_cc="${add_cc:-Y}"
  if [[ "${add_cc,,}" == "y" ]]; then
    if command -v jq >/dev/null 2>&1; then
      tmp="$(mktemp)"
      jq --arg url "$SSE_URL" \
        '.mcpServers.seleniumbase = {type:"sse", url:$url}' \
        "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
      ok "added to ${SETTINGS} — restart Claude Code to pick it up"
    else
      warn "jq not installed; showing config to add manually:"
      cat <<EOF
{
  "mcpServers": {
    "seleniumbase": { "type": "sse", "url": "${SSE_URL}" }
  }
}
EOF
    fi
  fi
else
  log "Claude Code settings not found — add this to your MCP client:"
  cat <<EOF

  {
    "mcpServers": {
      "seleniumbase": { "type": "sse", "url": "${SSE_URL}" }
    }
  }

EOF
fi

echo
ok "Setup complete."
echo "  • Stop:   docker compose down"
echo "  • Logs:   docker compose logs -f"
echo "  • Config: edit .env, then 'docker compose restart'"
