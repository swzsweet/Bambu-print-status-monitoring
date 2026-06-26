# Bambu Print Status & Access Token

English · [简体中文](./README.md)

A web app to monitor your Bambu Lab printer in real time and to obtain an Access Token for China-region accounts.

- **Live print status** — the browser connects **directly** to Bambu Cloud MQTT (`wss`) and subscribes to the printer's status, showing progress / ETA / state, nozzle / bed / chamber temperatures, layers, speed, AMS filament, and error codes (HMS). No persistent backend process required, so it can be deployed on static / serverless platforms like Vercel.
- **Get Access Token** — log in with phone number + SMS code (with Geetest slider captcha). This feature requires the backend (it calls Bambu's China-region API).
- **Extras** — English / Chinese switch, PWA ("Add to Home Screen"), local token cache with auto-restore, responsive for mobile / tablet / landscape.

## Feature vs. deployment

| Feature | Needs backend | Notes |
|---------|--------------|-------|
| Live print status | No | Browser connects to MQTT directly; front-end only |
| Get Access Token | Yes | Backend uses `curl_cffi` to call Bambu's China API |

> Note: the token endpoints hit Bambu's **China-region** servers. If the backend is hosted overseas (e.g. a Vercel US node), it may fail due to network or regional policy. In that case, **run locally once to obtain a token**, then paste that token into any deployed page to view status.

## Install

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

> Pillow in `requirements.txt` is only used to regenerate PWA icons (already generated under `static/icons/`); it's commented out and not needed to run the app.

## Run

```bash
python app.py
```

The console prints the access URLs:

```
Local:   http://127.0.0.1:5000
Phone:   http://<LAN-IP>:5000   (must be on the same Wi-Fi)
```

- Binds `0.0.0.0` by default so phones on the same LAN can reach it.
- Local only: `BAMBU_HOST=127.0.0.1 python app.py`.
- Custom port: `BAMBU_PORT=8080`.

## Usage

**Have a token:** paste the Access Token in "Bambu Print Status" → verify → pick a printer → live monitoring. The token and selected printer are cached in the browser and restored automatically on refresh/revisit.

**No token:** click "Log in by phone to get a token" below the verify area → enter your phone number in the dialog → get the code (complete the slider) → enter the code to log in → "View print status with this token".

## How it works

- The front-end uses [MQTT.js](https://github.com/mqttjs/MQTT.js) to connect directly to `wss://cn.mqtt.bambulab.com:8084/mqtt`, subscribes to `device/<serial>/report`, and merges incremental updates.
- The backend is Flask + `curl_cffi` (spoofs a browser TLS fingerprint to pass Bambu China's anti-bot). The MQTT username `u_<uid>` is parsed from the token or fetched via the preference API; the password is the token itself.
- API and MQTT protocol are based on the open-source project [greghesp/ha-bambulab](https://github.com/greghesp/ha-bambulab) (pybambu); for the China region, `.com` domains are replaced with `.cn`.

## Security

- **An Access Token is equivalent to your account credential** and can control your printers. Do not share it or commit it to public repos.
- The token is cached only in your browser's `localStorage`; clear it with "Clear cache" on the page.
- When bound to `0.0.0.0`, the service is exposed on your LAN — use it on a trusted network.
- During monitoring, the token is sent directly from your browser to Bambu's MQTT broker as the password (same as the official app).

## Feedback

Please file bugs or suggestions in [Issues](https://github.com/swzsweet/Bambu-print-status-monitoring/issues).

## Disclaimer

This is a personal, self-use learning tool and is not affiliated with Bambu Lab. You assume all responsibility for any consequences of use.
