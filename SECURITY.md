# Secure Deployment Guide

Parallax processes personal data — messages, documents, photos, decisions. This guide covers how to deploy it safely, whether for local-only use or with external messenger integrations.

---

## Local-Only Mode (Default — No Network Exposure)

Out of the box, Parallax binds to `127.0.0.1:8000`. Nothing is accessible from outside your machine.

```bash
# .env
API_HOST=127.0.0.1     # Localhost only
PARALLAX_API_KEY=       # Empty = no auth needed (safe because local)
USE_LOCAL_LLM=true      # All inference stays on-device via Ollama
```

In this mode:
- All data stays on disk in `./data/`
- LLM calls go to local Ollama (no external API traffic)
- The CLI and API are only accessible from your machine
- No ports are exposed to the network

This is the recommended setup for research use.

---

## Messenger Integration (Slack/Discord)

If you want the agent to respond on Slack or Discord, the connectors use **outbound connections only** — they connect to Slack/Discord's servers, not the other way around.

**Slack** uses Socket Mode (WebSocket outbound). No inbound webhook needed.  
**Discord** uses Gateway (WebSocket outbound). No inbound webhook needed.

This means **no ports need to be opened** for basic messenger integration:

```bash
# .env — add connector tokens
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_APP_TOKEN=xapp-your-token    # Socket Mode token
DISCORD_BOT_TOKEN=your-token

# API stays local
API_HOST=127.0.0.1
```

The agent responds on messaging platforms while the API and data remain local-only.

---

## Secure Tunnel (When External API Access Is Needed)

If you need to expose the API (e.g., for a remote dashboard, mobile app, or webhook integrations), use a secure tunnel instead of opening ports directly.

### Option 1: Cloudflare Tunnel (Recommended)

Zero-trust tunnel — no ports opened on your machine, traffic encrypted end-to-end, DDoS protection included.

```bash
# Install cloudflared
# macOS: brew install cloudflared
# Linux: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared && chmod +x cloudflared

# Authenticate (one-time)
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create parallax

# Configure
cat > ~/.cloudflared/config.yml << EOF
tunnel: parallax
credentials-file: /home/$USER/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: parallax.yourdomain.com
    service: http://127.0.0.1:8000
    originRequest:
      noTLSVerify: false
  - service: http_status:404
EOF

# Run
cloudflared tunnel run parallax
```

Then set in `.env`:
```bash
API_HOST=127.0.0.1               # Still localhost — tunnel handles exposure
PARALLAX_API_KEY=your-secret-key  # REQUIRED when tunnel is active
CORS_ORIGINS=https://parallax.yourdomain.com
```

### Option 2: WireGuard VPN

Point-to-point encrypted tunnel between your machine and a specific client. Best for single-user access from a known device.

```bash
# Install WireGuard
sudo apt install wireguard

# Generate keys
wg genkey | tee privatekey | wg pubkey > publickey

# Configure /etc/wireguard/wg0.conf
[Interface]
PrivateKey = <server-private-key>
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
PublicKey = <client-public-key>
AllowedIPs = 10.0.0.2/32
```

Then bind the API to the WireGuard interface:
```bash
API_HOST=10.0.0.1                 # WireGuard subnet only
PARALLAX_API_KEY=your-secret-key
```

### Option 3: SSH Tunnel (Quick & Simple)

For temporary access from another machine you control:

```bash
# From the remote machine
ssh -L 8000:127.0.0.1:8000 user@parallax-host

# API is now accessible at localhost:8000 on the remote machine
```

---

## Production Hardening Checklist

If deploying beyond personal use:

```
[x] PARALLAX_API_KEY set to a strong random value
[x] API_HOST=127.0.0.1 (behind reverse proxy or tunnel)
[x] CORS_ORIGINS set to specific allowed domains
[x] USE_LOCAL_LLM=true OR API keys stored in system keychain, not .env
[ ] Reverse proxy (nginx/Caddy) with TLS termination
[ ] Rate limiting (nginx limit_req or FastAPI middleware)
[ ] Log rotation configured
[ ] Database backups for decisions.db
[ ] File permissions: data/ directory readable only by service user
```

### Nginx Reverse Proxy (if not using tunnel)

```nginx
server {
    listen 443 ssl;
    server_name parallax.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/parallax.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/parallax.yourdomain.com/privkey.pem;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Data Flow Security

```
Your Data (local disk)
    │
    ▼
[Parallax API — 127.0.0.1:8000]
    │                    │
    ▼                    ▼
[Ollama local]    [Secure tunnel/VPN]
(no network)          │
                      ▼
              [External clients]
              (API key required)
              (TLS encrypted)
              (CORS restricted)
```

**Key principle:** Your personal data never leaves your machine. LLM inference can be fully local via Ollama. External access is optional, gated behind auth + encryption, and uses tunnels rather than open ports.

---

## Continuous Data Ingestion from Messengers

For ongoing data collection from Slack/Discord (not just one-time export):

The Slack and Discord connectors already log all interactions. To also ingest historical messages continuously:

```bash
# Slack — export channel history via API (requires appropriate scopes)
python -m phase1_data_pipeline.run_pipeline --source slack --continuous

# Discord — export via DiscordChatExporter or bot API
python -m phase1_data_pipeline.run_pipeline --source discord --continuous
```

The `--continuous` flag (when implemented) watches for new messages via the WebSocket connectors and feeds them into the pipeline in real-time, keeping the agent's memory current.

**Security note:** Continuous ingestion means the vector database grows over time. The authorization tiers still apply — messages from private channels stay tagged as private-tier and are never revealed to public-tier callers.
