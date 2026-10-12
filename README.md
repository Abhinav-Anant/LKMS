# Lotus Kids Management System (LKMS)

School management system for Lotus Kids School, Rajasthan.

## Layout

- `backend/` – Django + Django REST Framework API (from acharya)
- `frontend/` – React + TypeScript + Vite UI (from acharya)
- `whatsapp-server/` – WhatsApp messaging service (server part of Blastup)
- `docs/LKMS_PLAN.md` – build plan and phase breakdown

## Sources

- Base: [frankmathewsajan/acharya](https://github.com/frankmathewsajan/acharya) at commit `89409789dc3fd2fea8e378c632bed81f2cc40598`, used with the author's permission. Original README in `docs/ACHARYA_README.md`.
- WhatsApp server: [kalpintelligence/Blastup](https://github.com/kalpintelligence/Blastup) at commit `7a6df66cee12241f8d9f909392d37728942e84b2`, MIT licence (see `whatsapp-server/LICENSE`).

Removed on import: committed `node_modules/`, `backend/db.sqlite3` and `frontend/.env`.
