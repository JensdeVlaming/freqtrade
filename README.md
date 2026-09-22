# BTC V5 — Portainer paper-trading stack

Deploy the frozen BTC/USDT V5 strategy through a Git repository stack in **Portainer CE or BE on Docker Standalone** (not Docker Swarm). The image includes the strategy, public configuration and FreqUI; no host directories or relative-path-volume feature are needed.

**This is forward paper trading.** It uses real Binance market prices and a simulated 10,000 USDT wallet. No exchange credentials are needed. Both the configuration and the `--dry-run` command enable simulation. This repository does not provide a live-money deployment.

## 1. Wait for the image

After a push to `main`, the [Build paper-trading image workflow](https://github.com/JensdeVlaming/freqtrade/actions) validates and publishes:

- `ghcr.io/jensdevlaming/freqtrade:main`
- `ghcr.io/jensdevlaming/freqtrade:sha-<full-commit-sha>`

Both Linux AMD64 and ARM64 are supported. Wait for the workflow to turn green before deploying. The upstream Freqtrade 2026.8 image is pinned by digest. GitHub's built-in workflow token publishes the image; no repository secret needs to be created for publishing.

## 2. Give Portainer access

This GitHub repository is private. There are **two separate authentication steps**:

1. **Git repository:** use a GitHub credential that can read `JensdeVlaming/freqtrade`. A fine-grained personal access token restricted to this repository with **Contents: read** is sufficient. Enter it into the stack's Git authentication fields, not the repository URL.
2. **Container image:** in Portainer, open **Registries → Add registry → Custom registry**. Set URL to `ghcr.io`, enable authentication, username `JensdeVlaming`, and use a GitHub classic PAT with **read:packages** and access to this package. Authorize organization SSO if applicable. Grant the Portainer environment/user access to the registry if your edition requires it. Select this registry during stack deployment if that option is shown.

Keep these credentials in Portainer. They do not belong in this repository or the bot's environment. The package remains private by default; image publishing does not make it public.

## 3. Create the stack

In the target Docker environment, select **Stacks → Add stack → Repository**:

| Field | Value |
|---|---|
| Name | `btc-paper` |
| Repository URL | `https://github.com/JensdeVlaming/freqtrade.git` |
| Repository reference | `refs/heads/main` |
| Compose path | `compose.yaml` |
| Repository authentication | Enabled, using the Git credential above |
| Relative path volumes | Not needed |
| Automatic GitOps updates | Leave disabled for this frozen paper trial |

Under **Environment variables**, add:

| Name | Value |
|---|---|
| `UI_PASSWORD` | A strong, unique FreqUI login password |
| `JWT_SECRET` | A random secret of at least 32 bytes |
| `WS_TOKEN` | A different random secret of at least 32 bytes |
| `UI_USERNAME` | Optional; default `freqtrader` |
| `BIND_IP` | Optional; default `127.0.0.1`; use the Docker host's **LAN IP** for direct LAN access |
| `UI_PORT` | Optional; default `8080` |
| `IMAGE_TAG` | Recommended: `sha-<full-commit-sha>` from a successful build; default `main` |

Generate each random secret locally, separately, for example with `openssl rand -hex 32`. The three required values have no insecure defaults: Compose refuses deployment when one is missing or empty. Do not paste your values into chat or commit them.

Click **Deploy the stack**. Binance's public API must be reachable from the Docker host, and BTC/USDT must be available there. The bot retrieves its 721 hourly startup candles automatically. Market/API restrictions are not solved by changing the strategy's exchange or pair; such changes would need separate validation.

## 4. Open FreqUI and confirm operation

- With `BIND_IP` set to the host's LAN IP, open `http://<host-LAN-IP>:8080` (or your chosen `UI_PORT`). Keep this on a trusted network, or use an HTTPS reverse proxy for remote access.
- With the default loopback binding, use an SSH tunnel: `ssh -L 8080:127.0.0.1:8080 user@docker-host`, then open `http://localhost:8080`.
- Log in with `UI_USERNAME` and `UI_PASSWORD`.
- Confirm **dry-run**, strategy **DynamicBtc**, pair **BTC/USDT**, timeframe **1h**, and bot state **running**. Inspect container logs for successful exchange initialization and recurring heartbeats.
- An empty trade list is normal until a breakout occurs. Do not force trades just to test activity.

The health check verifies API responsiveness; it does **not** prove that Binance is reachable or that trading is running. Docker marks health failures but does not automatically restart unhealthy containers; `restart: unless-stopped` handles process exits.

## Persistence, updates and backups

The stack-scoped named volume `btc-paper_bot-data` (for the suggested stack name) holds:

- `tradesv3.paper.sqlite`: simulated trades and state;
- `logs/freqtrade.log`: bot logs (Freqtrade rotates the file; Docker output also has rotation).

Normal restart/redeploy preserves the volume. Keep the same stack name and do not delete the volume. A new stack name creates a separate paper account. The container runs as upstream's non-root `ftuser`, with the volume initialized to its ownership.

For a consistent backup, stop the stack, back up its **entire named volume**, then start it again. Restore while stopped. Never run two bots against the same SQLite database.

For updates, wait for the new GitHub build, record its full SHA, update `IMAGE_TAG` in Portainer, and redeploy. Prefer a tested SHA tag over floating `main` for reproducible trials. Leave wallet size and strategy parameters unchanged during the trial. Image rollback alone does not undo database migrations; use a matching backup if a future engine upgrade changes the schema.

## What the strategy does

- Buys when BTC breaks its previous 168-hour high while above its 720-hour simple moving average.
- Exits below its previous 72-hour low, or at its 15% position stop.
- One spot position at a time; no shorting, leverage or DCA.
- Sizes new entries using `wallet stake equity × 0.02 / stop distance`, subject to available funds and exchange limits. At a 15% stop this is roughly 13.33% of stake equity. The configured 99% tradable-balance ratio affects that equity. Size changes **between trades**, not continuously during a position.
- Nominal stop risk is about 2% of stake equity before fees, gaps and slippage; it is not a guaranteed loss ceiling.

`strategies/DynamicBtc.py` is byte-identical to the final V5 research candidate. `strategies/SHA256SUMS` records its hash. No post-evaluation strategy tuning was performed for this deployment.

## Evidence and limits

Final historical qualification: **2025-01-01 through 2026-09-20**, 10,000 USDT starting account:

| Metric | 0.1% fee per side | 0.2% fee per side |
|---|---:|---:|
| Trades | 29 | 29 |
| Net return over the whole period | +1.9563% | +1.1779% |
| Profit factor | 1.3265 | 1.1821 |
| Hourly sampled maximum drawdown | 3.6846% | 3.8605% |

Earlier optimization attempts did not beat the selected baseline's improvement thresholds. The final result qualified the baseline for paper observation, **not production trading or a guaranteed advantage**. Earlier historical exposure and a research file-access incident prevent calling it pristine unseen validation. Real fills, slippage, recovery behavior and prospective performance still require evidence. Paper execution cannot prove live fill quality.

Research datasets, old configurations, local credentials and historical trade databases are intentionally excluded from this deployment repository.

## Local validation

```sh
docker build -t btc-paper:verify .
docker run --rm --network none --entrypoint python \
  -v "$PWD/tests:/tests:ro" btc-paper:verify /tests/verify_image.py
```

The GitHub workflow also checks the frozen source hash, Compose interpolation, native Freqtrade configuration/strategy loading, bundled FreqUI and writable non-root data storage before publishing. These checks do not start a trading bot or require exchange/API credentials.

Optional: `python3 tests/smoke.py` briefly starts an isolated paper bot against Binance, checks its running heartbeat, API and database, and then stops/removes its own test container and anonymous volume. It publishes no ports and uses throwaway test credentials. This network-dependent check is not run in GitHub Actions.
