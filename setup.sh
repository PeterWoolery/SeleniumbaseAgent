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
# Extract KEY=default lines from .env.example (ignore comments, blank lines)
parse_example_keys() {
  grep -E '^[A-Z_][A-Z0-9_]*=' .env.example
}

# Sync: append any KEY present in .env.example but missing from .env
sync_env() {
  local added=()
  while IFS= read -r line; do
    local key="${line%%=*}"
    if ! grep -qE "^${key}=" .env; then
      echo "$line" >> .env
      added+=("$key")
    fi
  done < <(parse_example_keys)

  if [[ ${#added[@]} -gt 0 ]]; then
    warn "Added ${#added[@]} new config key(s) from .env.example (defaults applied):"
    printf "     - %s\n" "${added[@]}"
    echo "     Review/edit .env before continuing, then press Enter."
    read -r
  fi
}

if [[ -f .env ]]; then
  log ".env already exists — syncing any new keys from .env.example"
  sync_env
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
SSE_URL="http://localhost:${PORT}/sse"
USER_CONFIG="${HOME}/.claude.json"

print_manual_block() {
  cat <<EOF

  {
    "mcpServers": {
      "seleniumbase": { "type": "sse", "url": "${SSE_URL}" }
    }
  }

EOF
}

register_user_scope() {
  if ! command -v jq >/dev/null 2>&1; then
    warn "jq not installed; add this manually to ${USER_CONFIG} at top-level 'mcpServers':"
    print_manual_block
    return
  fi
  [[ -f "$USER_CONFIG" ]] || echo '{}' > "$USER_CONFIG"
  tmp="$(mktemp)"
  jq --arg url "$SSE_URL" \
    '.mcpServers.seleniumbase = {type:"sse", url:$url}' \
    "$USER_CONFIG" > "$tmp" && mv "$tmp" "$USER_CONFIG"
  ok "registered in ${USER_CONFIG} (user scope — available in all projects)"
}

register_project_scope() {
  local target="$1"
  [[ -d "$target" ]] || fail "directory not found: $target"
  local mcp_file="${target%/}/.mcp.json"
  if command -v jq >/dev/null 2>&1; then
    [[ -f "$mcp_file" ]] || echo '{}' > "$mcp_file"
    tmp="$(mktemp)"
    jq --arg url "$SSE_URL" \
      '.mcpServers.seleniumbase = {type:"sse", url:$url}' \
      "$mcp_file" > "$tmp" && mv "$tmp" "$mcp_file"
  else
    cat > "$mcp_file" <<EOF
{
  "mcpServers": {
    "seleniumbase": { "type": "sse", "url": "${SSE_URL}" }
  }
}
EOF
  fi
  ok "wrote ${mcp_file} (project scope — this project only)"
}

echo
log "Register 'seleniumbase' with Claude Code?"
echo "  1) user scope     — available in all projects (~/.claude.json)"
echo "  2) project scope  — single project (.mcp.json in that directory)"
echo "  3) skip           — show config for manual setup"
read -r -p "Choice [1/2/3] (default 1): " scope_choice
scope_choice="${scope_choice:-1}"

case "$scope_choice" in
  1)
    register_user_scope
    ;;
  2)
    read -r -p "Project directory (default: current working directory): " proj_dir
    proj_dir="${proj_dir:-$PWD}"
    register_project_scope "$proj_dir"
    ;;
  *)
    log "Skipping registration. Add this to your MCP client:"
    print_manual_block
    ;;
esac

echo "Restart Claude Code to load the server."

echo
ok "Setup complete."
echo "  • Stop:   docker compose down"
echo "  • Logs:   docker compose logs -f"
echo "  • Config: edit .env, then 'docker compose restart'"
