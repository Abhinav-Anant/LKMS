# Setting up LKMS on a server

This guide puts LKMS on one rented Linux server (a VPS) so staff and parents can use it at your own web address,
for example `https://lkms.lotuskids.in`. Follow the steps in order. Every command is typed on the server unless it
says otherwise. Where you see `lkms.lotuskids.in`, use your real address.

Expect it to take an afternoon. Someone comfortable with a Linux command line should do it; nothing here needs
programming.

What ends up on the server:

| Part | What it does |
| --- | --- |
| Nginx | the web server: serves the website, HTTPS certificate, passes `/api/` and `/admin/` to Django |
| Gunicorn (`lkms-web`) | runs the Django back end |
| PostgreSQL | the database |
| `lkms-whatsapp-sender` | sends queued WhatsApp messages |
| WhatsApp server (Docker) | Blastup, linked to the school's phone |
| `lkms-backup.timer` | nightly backup at 02:30 |
| `lkms-fee-reminders.timer` | fee reminders every morning at 10:00 |

The config files for all of these are in the `deploy/` folder of the code.

---

## 1. What you need first

- **A VPS** running **Ubuntu 24.04 LTS**: 2 CPUs, 4 GB RAM, at least 40 GB disk. Pick a data centre in India
  (for example Mumbai) so the site is fast and student data stays in the country. Any provider works
  (DigitalOcean, AWS Lightsail, Hetzner, E2E Networks and others).
- **A domain name** you control, e.g. `lotuskids.in`. In its DNS settings, add an **A record** for `lkms`
  (or whatever name you choose) pointing to the server's IP address. Do this first: it can take up to an hour to work.
- **The school's WhatsApp phone** for step 7 (a number used normally for a while, not a brand-new SIM).
- **Access to the GitHub repository** `Abhinav-Anant/LKMS`.

## 2. First login and basic security

Log in as root with the password or key the provider gave you (`ssh root@SERVER-IP`), then:

```bash
apt update && apt -y upgrade
timedatectl set-timezone Asia/Kolkata

# A personal admin account, so you stop using root
adduser abhinav                      # choose a strong password
usermod -aG sudo abhinav
```

From your own computer, copy your SSH key to the new account (`ssh-copy-id abhinav@SERVER-IP`), check you can log
in with it, then turn off password and root logins:

```bash
sudo nano /etc/ssh/sshd_config.d/99-lkms.conf
```

with these two lines:

```
PasswordAuthentication no
PermitRootLogin no
```

then `sudo systemctl restart ssh`. Keep your current session open until you have checked a new login works.

Firewall and automatic security updates:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable
sudo apt -y install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades      # answer Yes
```

From here on, work as your admin account (`abhinav`), using `sudo` where shown.

## 3. Install the software

```bash
sudo apt -y install postgresql nginx certbot python3-certbot-nginx git curl ca-certificates

# uv (runs the Python back end)
curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin sh

# Node.js 22 (builds the website)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
sudo apt -y install nodejs

# Docker (runs the WhatsApp server)
curl -fsSL https://get.docker.com | sudo sh
```

Check: `psql --version` shows 16, `uv --version`, `node --version` shows v22, `docker --version`.

## 4. A user and folders for LKMS

LKMS runs as its own user, `lkms`, which cannot log in with a password.

```bash
sudo adduser --system --group --home /home/lkms --shell /bin/bash lkms
sudo mkdir -p /srv/lkms /srv/lkms-data
sudo chown lkms:lkms /srv/lkms /srv/lkms-data
sudo chmod 700 /srv/lkms-data
```

`/srv/lkms` holds the code. `/srv/lkms-data` holds uploaded documents and backups, readable only by `lkms`.

## 5. Get the code

The repository is private, so the server needs a read-only **deploy key**:

```bash
sudo -u lkms mkdir -p -m 700 /home/lkms/.ssh
sudo -u lkms ssh-keygen -t ed25519 -N "" -f /home/lkms/.ssh/id_ed25519
sudo cat /home/lkms/.ssh/id_ed25519.pub
```

On GitHub open the repository, **Settings > Deploy keys > Add deploy key**, paste the line that was printed,
title it "LKMS server" and leave **Allow write access** unticked. Then:

```bash
sudo -u lkms git clone git@github.com:Abhinav-Anant/LKMS.git /srv/lkms
```

(Answer `yes` when asked about GitHub's fingerprint.)

## 6. Run the setup wizard

The wizard asks for every setting LKMS needs, **one question at a time**, each with a short explanation and a
suggested answer in `[brackets]` (press Enter to accept it). Then it offers to do the rest of the setup for you.

```bash
sudo python3 /srv/lkms/deploy/setup_wizard.py
```

**Part 1, settings.** It asks for:

| Question | Example |
| --- | --- |
| Website address | `lkms.lotuskids.in` |
| Database name, user, password, server and port | press Enter for each; a random password is suggested |
| Folder for documents and backups | `/srv/lkms-data` |
| Largest upload in MB | 5 |
| School UPI ID, account name and (optionally) a new QR picture | `8619190956@SBI`, Lotus Kids Education Society |
| WhatsApp alerts on or off; messages per minute, per parent per day, quiet hours | yes, 8, 6, `21,7` |
| Backups to keep (daily, weekly, monthly) and an optional off-site copy command | 14, 8, 12 |

It shows a summary and saves only when you say yes. It writes `backend/.env` (and `whatsapp-server/.env` with
random secrets, if WhatsApp is on), readable only by `lkms`. The Django secret key is made for you.

**Part 2, setting up the server.** Each step asks first, so you can skip one you have already done:

1. Creates the documents and backups folders.
2. Creates the database user and database (or updates the password).
3. Starts the WhatsApp server in Docker and connects LKMS to it.
4. Installs LKMS: Python and web packages, database tables, the website build, and Django's safety checks.
5. Asks for **the school's details**, again one at a time: name, address, PIN code, phone, UDISE+ code, board,
   admission-number format, the school year's dates, the classes and sections, the fee structure (how often fees
   are collected, the due day, and the tuition, admission, annual, exam and any other fee, either the same for every
   class or class by class), and the **administrator login** (username and password).
6. Turns on the website, gets the free HTTPS certificate (it asks for an email for expiry notices), and starts the
   nightly backup, the morning fee reminders and the WhatsApp sender. The DNS record from step 1 must already
   point at the server.

When it finishes, open `https://lkms.lotuskids.in/staff/login` and sign in as the administrator. Under **Users**, add
the principal, office, accountant and teachers (each gets a temporary password and must change it at first
sign-in). Under **School setup**, check the subjects, periods, admission documents and grade scale: standard ones
were filled in.

If a step fails, the wizard says what went wrong and stops. Fix it and run the wizard again: everything you
answered is kept and offered as the default, and the secret key and passwords are not changed unless you type new
ones. Run it again the same way whenever a setting changes (for example a new UPI ID), and answer **n** to the
steps that are already done. To see what it would do without changing anything, add `--dry-run`. To change only the
school's details: `cd /srv/lkms/backend && sudo -u lkms .venv/bin/python manage.py setup_school`.

Keep a copy of `backend/.env` and `whatsapp-server/.env` in a password manager: they are not in the backups, and
the secret key and passwords are needed to restore on a new server. Never put them on GitHub.

## 7. Link the school's WhatsApp phone

If you turned WhatsApp on in the wizard, sign in as principal, open **WhatsApp**, press **Link the school's phone**
and scan the QR code with the school's phone (WhatsApp > Settings > Linked devices > Link a device). Send yourself a
test: post a notice to one class with "Also send to parents on WhatsApp" ticked, using a class that has your own
number as a parent. Full details are in `WHATSAPP.md`.

## 8. Check the backups

The wizard turned on the nightly backup and took the first one. Check it:

```bash
sudo -u lkms /srv/lkms/backend/.venv/bin/python /srv/lkms/backend/manage.py backup --list
```

If you did not give an off-site copy command in the wizard, set one up now (`BACKUPS.md`, "Off-site copy"): a
backup that only exists on this server is lost with the server. Before the school starts using LKMS, **test a
restore** once, as described in `BACKUPS.md`.

The principal's dashboard shows a red warning if no backup has been taken for 36 hours.

## 9. Check everything is running

```bash
systemctl status lkms-web lkms-whatsapp-sender --no-pager
systemctl list-timers 'lkms-*' certbot.timer --no-pager
sudo docker compose -f /srv/lkms/docker-compose.yml ps
```

You should see both services running, three timers (backup, fee reminders, certificate renewal) with a next run
time, and the `whatsapp`, `mongo` and `redis` containers up.

---

## Updating to a new version

When new code has been pushed to GitHub:

```bash
sudo -u lkms /srv/lkms/deploy/update.sh
sudo systemctl restart lkms-web lkms-whatsapp-sender
```

The script takes a backup first, pulls the code, installs anything new, updates the database, rebuilds the website
and runs Django's checks. If it stops with an error, nothing has been restarted, so the site keeps running the old
version; send the error to whoever maintains LKMS.

If the WhatsApp server code changed (`whatsapp-server/`), also run
`cd /srv/lkms && sudo docker compose up -d --build whatsapp`.

## Troubleshooting

| Problem | Look here |
| --- | --- |
| Site does not load at all | `sudo nginx -t`, `sudo systemctl status nginx`, and that the DNS A record points at this server (`ping lkms.lotuskids.in`) |
| "502 Bad Gateway" | the back end is not running: `sudo journalctl -u lkms-web -n 50` |
| "400 Bad Request" on every page | `DJANGO_ALLOWED_HOSTS` in `backend/.env` does not match the address; fix it and `sudo systemctl restart lkms-web` |
| Sign-in works but saving fails with a CSRF error | `DJANGO_CSRF_TRUSTED_ORIGINS` must be `https://` plus the address |
| Uploading a document fails | the file is over 5 MB, or `/srv/lkms-data` is not owned by `lkms` |
| WhatsApp messages stay "queued" | `sudo journalctl -u lkms-whatsapp-sender -n 50`, and the **WhatsApp** page in the app (phone linked?) |
| Backup warning on the dashboard | `sudo journalctl -u lkms-backup -n 50`; disk full? (`df -h`) |
| Certificate expired | `sudo certbot renew --dry-run` shows why renewal fails |

All logs: `sudo journalctl -u 'lkms-*' --since today`.

## Before the school starts using it

- [ ] The real school details, classes, fees and staff accounts are entered (step 6).
- [ ] The placeholder formats in `BOARD_CHECKS.md` are confirmed or replaced.
- [ ] Backups run nightly, the off-site copy works, and one restore has been tested.
- [ ] WhatsApp is linked and a test message arrived.
- [ ] Every staff member has their own account; nobody shares the administrator login.
- [ ] A copy of `backend/.env` and `whatsapp-server/.env` is stored safely off the server.

## Setting up by hand (without the wizard)

The wizard runs these same steps. Use this section if you prefer to do them yourself, or to see exactly what
the wizard did.

### The database

Make up a long random password for the database (for example run
`python3 -c "import secrets; print(secrets.token_urlsafe(24))"`) and keep it for the settings below.

```bash
sudo -u postgres createuser --pwprompt lkms        # type the password twice
sudo -u postgres createdb --owner lkms lkms
```

PostgreSQL only listens on the server itself, so it is not reachable from the internet.

### Settings (`backend/.env`)

```bash
sudo -u lkms cp /srv/lkms/backend/.env.example /srv/lkms/backend/.env
sudo chmod 600 /srv/lkms/backend/.env
sudo -u lkms nano /srv/lkms/backend/.env
```

Change these lines (leave the rest as they are):

```
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=          <- paste the output of: python3 -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_ALLOWED_HOSTS=lkms.lotuskids.in
DJANGO_CSRF_TRUSTED_ORIGINS=https://lkms.lotuskids.in
CORS_ALLOWED_ORIGINS=https://lkms.lotuskids.in
DATABASE_URL=postgres://lkms:THE-DATABASE-PASSWORD@localhost:5432/lkms
PRIVATE_MEDIA_ROOT=/srv/lkms-data/private_media
BACKUP_DIR=/srv/lkms-data/backups
FRONTEND_BASE_URL=https://lkms.lotuskids.in
```

Keep a copy of this file in a password manager: it is not in the backups, and the secret key and passwords are
needed to restore on a new server. Never put it on GitHub.

### Install and prepare LKMS

```bash
cd /srv/lkms/backend
sudo -u lkms uv sync --frozen --no-dev
sudo -u lkms .venv/bin/python manage.py migrate
sudo -u lkms .venv/bin/python manage.py collectstatic --noinput
sudo -u lkms .venv/bin/python manage.py seed_lkms_defaults
sudo -u lkms .venv/bin/python manage.py createsuperuser       # your administrator login, e.g. username "abhinav"
sudo -u lkms .venv/bin/python manage.py shell -c \
  "from users.models import User; User.objects.filter(username='abhinav').update(role='admin')"
sudo -u lkms .venv/bin/python manage.py check --deploy

cd /srv/lkms/frontend
sudo -u lkms npm ci --no-audit --no-fund
sudo -u lkms npm run build
```

The `shell -c` line gives that login the Administrator role (put in the username you chose).
`seed_lkms_defaults` creates the placeholder classes, subjects, periods, fee heads and grade scale; the school
changes them later in the app. `check --deploy` may show one warning about `SECURE_HSTS_PRELOAD`; that one is fine.

### Start the website with HTTPS

```bash
# The back end
sudo cp /srv/lkms/deploy/lkms-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lkms-web
sudo systemctl status lkms-web          # should say "active (running)"

# The web server
sudo cp /srv/lkms/deploy/nginx-lkms.conf /etc/nginx/sites-available/lkms
sudo sed -i 's/school.example.in/lkms.lotuskids.in/' /etc/nginx/sites-available/lkms
sudo ln -s /etc/nginx/sites-available/lkms /etc/nginx/sites-enabled/lkms
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# The HTTPS certificate (free, from Let's Encrypt; renews itself)
sudo certbot --nginx -d lkms.lotuskids.in --redirect -m office@lotuskids.in --agree-tos
```

Open `https://lkms.lotuskids.in` in a browser: the school's home page should load with a padlock. Then go to
`https://lkms.lotuskids.in/staff/login` and sign in with the administrator created above.

If something does not load, see **Troubleshooting** at the end.

### Set up the school in the app

Signed in as administrator:

1. `https://lkms.lotuskids.in/admin/` > **School profile**: the school's name, address, phone, UDISE+ code,
   affiliation number and admission-number format.
2. **School setup**: sessions, classes, sections, subjects, periods and class teachers.
3. **Fees > Setup**: the real fee heads and amounts (the seeded ones are placeholders).
4. **Users**: add the principal, office, accountant and teachers. Each gets a temporary password and must change it
   at first sign-in.

The guides for each part are `ADMISSIONS.md`, `FEES.md`, `PORTALS.md` and `EXAMS.md`.

### WhatsApp

Full details are in `WHATSAPP.md`. In short:

```bash
cd /srv/lkms
sudo -u lkms cp whatsapp-server/.env.example whatsapp-server/.env
sudo chmod 600 whatsapp-server/.env
sudo -u lkms nano whatsapp-server/.env      # fill JWT_SECRET, COOKIE_SECRET and ADMIN_PASSWORD with long random values

sudo docker compose up -d whatsapp          # starts the WhatsApp server with its MongoDB and Redis
sudo docker compose run --rm whatsapp node dist/scripts/lkms-api-key.js
```

Only start the `whatsapp` service: the `postgres` service in `docker-compose.yml` is for development, and the
server uses the PostgreSQL installed in step 3 of the guide.

Copy the printed `WHATSAPP_API_KEY=...` line into `backend/.env` and set `WHATSAPP_ENABLED=true`. Then start the
sender:

```bash
sudo cp /srv/lkms/deploy/lkms-whatsapp-sender.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lkms-whatsapp-sender
sudo systemctl restart lkms-web
```

Sign in as principal, open **WhatsApp**, press **Link the school's phone** and scan the QR code with the school's
phone (WhatsApp > Settings > Linked devices > Link a device). Send yourself a test: post a notice to one class with
"Also send to parents on WhatsApp" ticked, using a class that has your own number as a parent.

### Backups

Full details are in `BACKUPS.md`.

```bash
sudo cp /srv/lkms/deploy/lkms-backup.service /srv/lkms/deploy/lkms-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lkms-backup.timer
sudo systemctl start lkms-backup.service                  # the first backup, now
sudo -u lkms /srv/lkms/backend/.venv/bin/python /srv/lkms/backend/manage.py backup --list
```

Then set up the **off-site copy** (`BACKUPS.md`, "Off-site copy"): a backup that only exists on this server is lost
with the server. Before the school starts using LKMS, **test a restore** once, as described in `BACKUPS.md`.

The principal's dashboard shows a red warning if no backup has been taken for 36 hours.

### Fee reminders

```bash
sudo cp /srv/lkms/deploy/lkms-fee-reminders.service /srv/lkms/deploy/lkms-fee-reminders.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lkms-fee-reminders.timer
```

Reminders go out at 10:00 for fees due in 3 days, and every 7 days while a fee is overdue (`FEES.md`).

## Tested

On 13 Oct 2026 the manual steps (database, settings, install, website, backups) and the update script were run on a scratch Ubuntu 24.04 machine with
PostgreSQL 16 and Nginx 1.24, using a stand-in certificate in place of certbot: the website, staff pages, API,
Django admin, backups (and the dashboard's backup status) and an update from GitHub all worked, and the systemd
files passed `systemd-analyze verify`. Not tested there: Let's Encrypt itself (it needs a real domain), and the
WhatsApp server in Docker with a real phone.

The setup wizard was then run on the same machine as root, answering each question as a person would: it
created the folders and a new database, wrote `backend/.env`, installed LKMS, saved the school's details,
fees and administrator, and the administrator could sign in. Its last step (systemd, Nginx, certbot) runs the
same commands as the manual steps above; it was checked with `--dry-run` only.
