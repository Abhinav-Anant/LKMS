#!/usr/bin/env python3
"""LKMS setup wizard.

Asks for every setting LKMS needs, one question at a time, writes backend/.env (and
whatsapp-server/.env), then offers to do the rest of the server setup: database,
folders, install, the school's details, the website and HTTPS.

On the server, after getting the code (docs/DEPLOY.md steps 1 to 6):

    sudo python3 /srv/lkms/deploy/setup_wizard.py

Safe to run again: the current values become the defaults, and the secret key and
passwords are kept unless you type new ones. Uses only Python's standard library, so
it works before LKMS itself is installed.
"""

import argparse
import getpass
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

DEFAULT_REPO = Path(__file__).resolve().parent.parent
SERVER_REPO = Path("/srv/lkms")
APP_USER = "lkms"

URL_SAFE = re.compile(r"^[A-Za-z0-9_.~-]+$")
DB_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,30}$")
DOMAIN = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------------------------------------------------------------- asking


def say(text=""):
    print(textwrap.fill(text, width=88) if text else "")


def explain(text):
    for line in textwrap.wrap(text, width=84):
        print("  " + line)


def ask(question, help="", default="", check=None, secret=False):
    """Ask one question until the answer passes `check` (which returns an error message or None)."""
    print()
    print(question)
    if help:
        explain(help)
    while True:
        if secret:
            hint = " (press Enter to keep the current one)" if default else ""
            raw = getpass.getpass(f"> {hint} ")
        else:
            raw = input(f"> [{default}] " if default else "> ")
        value = raw.strip() or default
        error = check(value) if check else (None if value else "Please type an answer.")
        if error:
            print(f"  ! {error}")
            continue
        return value


def ask_yes(question, help="", default=True):
    print()
    print(question)
    if help:
        explain(help)
    while True:
        raw = input("> [Y/n] " if default else "> [y/N] ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  ! Please answer y or n.")


def optional(value):
    return None


def whole_number(low, high):
    def check(value):
        if not value.isdigit() or not low <= int(value) <= high:
            return f"Type a whole number from {low} to {high}."
        return None
    return check


def check_domain(value):
    if not DOMAIN.match(value):
        return "Type only the address, like erp.yourschool.in (no https://, no slash at the end)."
    return None


def check_password(value):
    if len(value) < 16 or not URL_SAFE.match(value):
        return "Use at least 16 characters: letters, digits, - _ . or ~ only."
    return None


def check_db_name(value):
    return None if DB_NAME.match(value) else "Use small letters, digits and _ only, starting with a letter."


def check_absolute(value):
    return None if value.startswith("/") else "Type a full path starting with /."


def check_quiet_hours(value):
    parts = value.split(",")
    if len(parts) != 2 or not all(p.strip().isdigit() and 0 <= int(p) <= 23 for p in parts):
        return "Type two hours from 0 to 23 separated by a comma, like 21,7."
    return None


def check_email(value):
    return None if EMAIL.match(value) else "Type an email address, like office@yourschool.in."


# ---------------------------------------------------------------- .env files


def read_env(path):
    """KEY=value pairs from an .env file, in file order. Comments and blank lines are skipped."""
    values = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


# The order and comments of the backend .env written by the wizard.
BACKEND_LAYOUT = [
    ("Website", ["DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS", "DJANGO_CSRF_TRUSTED_ORIGINS",
                 "CORS_ALLOWED_ORIGINS", "FRONTEND_BASE_URL"]),
    ("Database", ["DATABASE_URL"]),
    ("Files", ["PRIVATE_MEDIA_ROOT", "MAX_UPLOAD_SIZE_MB", "LOG_LEVEL"]),
    ("WhatsApp alerts (docs/WHATSAPP.md)", ["WHATSAPP_ENABLED", "WHATSAPP_API_URL", "WHATSAPP_API_KEY",
                                            "WHATSAPP_RATE_PER_MINUTE", "WHATSAPP_DAILY_LIMIT_PER_NUMBER",
                                            "WHATSAPP_QUIET_HOURS"]),
    ("Backups (docs/BACKUPS.md)", ["BACKUP_DIR", "BACKUP_KEEP_DAILY", "BACKUP_KEEP_WEEKLY", "BACKUP_KEEP_MONTHLY",
                                   "BACKUP_COPY_COMMAND"]),
]


def render_env(values, layout, title):
    lines = [f"# {title}", f"# Written by deploy/setup_wizard.py on {datetime.now():%d %b %Y %H:%M}.",
             "# Keep a copy somewhere safe off the server. Never put it on GitHub.", ""]
    placed = set()
    for heading, keys in layout:
        lines.append(f"# {heading}")
        for key in keys:
            if key in values:
                lines.append(f"{key}={values[key]}")
                placed.add(key)
        lines.append("")
    others = [key for key in values if key not in placed]
    if others:
        lines.append("# Other settings")
        lines += [f"{key}={values[key]}" for key in others]
        lines.append("")
    return "\n".join(lines)


def database_url(name, user, password, host, port):
    return f"postgres://{user}:{password}@{host}:{port}/{name}"


def parse_database_url(url):
    if not url.startswith("postgres"):
        return {}
    parts = urlsplit(url)
    return {
        "name": parts.path.lstrip("/"), "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""), "host": parts.hostname or "", "port": str(parts.port or ""),
    }


def first_domain(hosts):
    for host in hosts.split(","):
        host = host.strip()
        if DOMAIN.match(host.lower()):
            return host.lower()
    return ""


def backend_values(answers, current):
    """The backend .env from the answers, keeping settings the wizard does not ask about."""
    domain = answers["domain"]
    values = dict(current)
    values.update({
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": current.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50),
        "DJANGO_ALLOWED_HOSTS": domain,
        "DJANGO_CSRF_TRUSTED_ORIGINS": f"https://{domain}",
        "CORS_ALLOWED_ORIGINS": f"https://{domain}",
        "FRONTEND_BASE_URL": f"https://{domain}",
        "DATABASE_URL": database_url(answers["db_name"], answers["db_user"], answers["db_password"],
                                     answers["db_host"], answers["db_port"]),
        "PRIVATE_MEDIA_ROOT": f"{answers['data_dir']}/private_media",
        "MAX_UPLOAD_SIZE_MB": answers["max_upload_mb"],
        "LOG_LEVEL": current.get("LOG_LEVEL") or "INFO",
        "WHATSAPP_ENABLED": "true" if answers["whatsapp"] and current.get("WHATSAPP_API_KEY") else "false",
        "WHATSAPP_API_URL": current.get("WHATSAPP_API_URL") or "http://127.0.0.1:3001",
        "WHATSAPP_API_KEY": current.get("WHATSAPP_API_KEY", ""),
        "WHATSAPP_RATE_PER_MINUTE": answers["wa_rate"],
        "WHATSAPP_DAILY_LIMIT_PER_NUMBER": answers["wa_daily"],
        "WHATSAPP_QUIET_HOURS": answers["wa_quiet"].replace(" ", ""),
        "BACKUP_DIR": f"{answers['data_dir']}/backups",
        "BACKUP_KEEP_DAILY": answers["keep_daily"],
        "BACKUP_KEEP_WEEKLY": answers["keep_weekly"],
        "BACKUP_KEEP_MONTHLY": answers["keep_monthly"],
        "BACKUP_COPY_COMMAND": answers["copy_command"],
    })
    return values


def whatsapp_values(current):
    """whatsapp-server/.env: the example's settings, with the three secrets filled in once."""
    values = dict(current)
    for key, size in (("JWT_SECRET", 48), ("COOKIE_SECRET", 48), ("ADMIN_PASSWORD", 24)):
        if not values.get(key):
            values[key] = secrets.token_urlsafe(size)
    values.setdefault("ADMIN_USERNAME", "lkms-admin")
    return values


def save_env(path, text, owner):
    """Write an .env readable only by its owner, keeping the previous file as .env.bak-<time>."""
    if path.exists():
        backup = path.with_name(f"{path.name}.bak-{datetime.now():%Y%m%d-%H%M%S}")
        shutil.copy2(path, backup)
        os.chmod(backup, 0o600)
        chown(backup, owner)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)
    os.chmod(path, 0o600)
    chown(path, owner)


def chown(path, owner):
    if owner and os.geteuid() == 0:
        shutil.chown(path, owner, owner)


# ---------------------------------------------------------------- questions


def ask_settings(current, whatsapp_set_up=False, school=None):
    school = school or {}
    db = parse_database_url(current.get("DATABASE_URL", ""))
    answers = {}

    say()
    say("== Part 1 of 2: settings ==")
    say("Press Enter to accept the value in [brackets].")

    print("\n-- 1. Website address --")
    answers["domain"] = ask(
        "What address will people type to open LKMS?",
        "The domain or sub-domain bought for the school, without https://, for example erp.yourschool.in. "
        "Its DNS 'A record' must point at this server's IP address before HTTPS can be switched on.",
        default=first_domain(current.get("DJANGO_ALLOWED_HOSTS", "")) or school.get("domain", ""),
        check=lambda v: check_domain(v.lower()),
    ).lower()

    print("\n-- 2. Database --")
    answers["db_name"] = ask("Database name?", "Where all school records are kept. The default is fine.",
                             default=db.get("name") or "lkms", check=check_db_name)
    answers["db_user"] = ask("Database user?", "The PostgreSQL login LKMS uses. The default is fine.",
                             default=db.get("user") or "lkms", check=check_db_name)
    answers["db_password"] = ask(
        "Database password?",
        "Press Enter to use the one shown (or the current one). LKMS stores it in backend/.env, so nobody needs to "
        "remember it.",
        default=db.get("password") or secrets.token_urlsafe(24), check=check_password,
        secret=bool(db.get("password")),
    )
    answers["db_host"] = ask("Database server?", "'localhost' when PostgreSQL runs on this same server.",
                             default=db.get("host") or "localhost")
    answers["db_port"] = ask("Database port?", "PostgreSQL's port. Almost always 5432.",
                             default=db.get("port") or "5432", check=whole_number(1, 65535))

    print("\n-- 3. Files --")
    media = current.get("PRIVATE_MEDIA_ROOT", "")
    answers["data_dir"] = ask(
        "Folder for uploaded documents and backups?",
        "Students' documents go in its 'private_media' folder and backups in its 'backups' folder. Only LKMS can "
        "read it. Choose a disk with plenty of room.",
        default=media.rsplit("/private_media", 1)[0] if media.endswith("/private_media") else
        school.get("data_dir", "/srv/lkms-data"),
        check=check_absolute,
    ).rstrip("/")
    answers["max_upload_mb"] = ask("Largest document a parent or staff member may upload, in MB?",
                                   "Phone photos of documents are usually 1 to 4 MB.",
                                   default=current.get("MAX_UPLOAD_SIZE_MB") or "5", check=whole_number(1, 50))

    print("\n-- 4. WhatsApp alerts --")
    answers["whatsapp"] = ask_yes(
        "Send WhatsApp alerts to parents (fees, attendance, notices, results)?",
        "Uses the school's own WhatsApp number, linked by scanning a QR code later. Needs Docker on this server. "
        "You can say no now and run this wizard again later.",
        default=whatsapp_set_up or current.get("WHATSAPP_ENABLED", "").lower() == "true"
        or (not current and school.get("whatsapp", True)),
    )
    answers["wa_rate"] = current.get("WHATSAPP_RATE_PER_MINUTE") or "8"
    answers["wa_daily"] = current.get("WHATSAPP_DAILY_LIMIT_PER_NUMBER") or "6"
    answers["wa_quiet"] = current.get("WHATSAPP_QUIET_HOURS") or "21,7"
    if answers["whatsapp"]:
        answers["wa_rate"] = ask("Most messages to send per minute?",
                                 "Sending slowly keeps WhatsApp from blocking the school's number. 8 is safe.",
                                 default=answers["wa_rate"], check=whole_number(1, 30))
        answers["wa_daily"] = ask("Most messages one parent may get in a day?",
                                  "Stops a parent being flooded if many things happen at once.",
                                  default=answers["wa_daily"], check=whole_number(1, 50))
        answers["wa_quiet"] = ask("Quiet hours (no messages sent), as start,end on the 24-hour clock?",
                                  "21,7 means nothing is sent from 9 pm to 7 am; messages wait until morning.",
                                  default=answers["wa_quiet"], check=check_quiet_hours)

    print("\n-- 5. Backups --")
    answers["keep_daily"] = ask("How many daily backups to keep?", "One backup is taken every night at 02:30.",
                                default=current.get("BACKUP_KEEP_DAILY") or "14", check=whole_number(1, 90))
    answers["keep_weekly"] = ask("How many weekly backups to keep?", "",
                                 default=current.get("BACKUP_KEEP_WEEKLY") or "8", check=whole_number(0, 52))
    answers["keep_monthly"] = ask("How many monthly backups to keep?", "",
                                  default=current.get("BACKUP_KEEP_MONTHLY") or "12", check=whole_number(0, 60))
    answers["copy_command"] = ask(
        "Command that copies each backup off this server? (optional)",
        "A backup only on this server is lost with the server. {file} is replaced by the backup's path, for "
        "example: rclone copy {file} gdrive:lkms-backups. Press Enter to leave it empty and set it up later "
        "(docs/BACKUPS.md).",
        default=current.get("BACKUP_COPY_COMMAND") or school.get("backup_copy_command", ""), check=optional,
    )
    return answers


def summary(answers):
    rows = [
        ("Website", f"https://{answers['domain']}"),
        ("Database", f"{answers['db_name']} (user {answers['db_user']}) on {answers['db_host']}:{answers['db_port']}"),
        ("Documents", f"{answers['data_dir']}/private_media (up to {answers['max_upload_mb']} MB each)"),
        ("Backups", f"{answers['data_dir']}/backups, keep {answers['keep_daily']} daily, {answers['keep_weekly']} "
                    f"weekly, {answers['keep_monthly']} monthly"),
        ("Off-site copy", answers["copy_command"] or "not set yet"),
        ("WhatsApp", f"on, {answers['wa_rate']}/minute, {answers['wa_daily']} a day per parent, quiet "
                     f"{answers['wa_quiet']}" if answers["whatsapp"] else "off"),
    ]
    print("\nYour answers:")
    for label, value in rows:
        print(f"  {label + ':':15} {value}")


# ---------------------------------------------------------------- doing


class Runner:
    def __init__(self, repo, dry_run):
        self.repo = repo
        self.dry_run = dry_run
        self.root = os.geteuid() == 0

    def run(self, command, as_app=False, cwd=None, stdin=None, capture=False, check=True):
        if as_app and self.root:
            command = ["runuser", "-u", APP_USER, "--"] + command
        print("  $ " + " ".join(command))
        if self.dry_run:
            return subprocess.CompletedProcess(command, 0, "", "")
        result = subprocess.run(command, cwd=cwd or self.repo, input=stdin, text=True,
                                capture_output=capture)
        if check and result.returncode != 0:
            raise StepFailed(" ".join(command), result.stderr if capture else "")
        return result


class StepFailed(Exception):
    pass


def create_folders(runner, answers):
    data = Path(answers["data_dir"])
    print(f"\nCreating {data}/private_media and {data}/backups")
    if runner.dry_run:
        return
    for path in (data, data / "private_media", data / "backups"):
        path.mkdir(parents=True, exist_ok=True)
        os.chmod(path, 0o700)
        if runner.root:
            chown(path, APP_USER)


def create_database(runner, answers):
    # Passed on standard input so the password never shows in the process list.
    script = "\n".join([
        f"\\set u '{answers['db_user']}'",
        f"\\set p '{answers['db_password']}'",
        f"\\set d '{answers['db_name']}'",
        "SELECT format('CREATE ROLE %I LOGIN', :'u') WHERE NOT EXISTS "
        "(SELECT 1 FROM pg_roles WHERE rolname = :'u') \\gexec",
        "SELECT format('ALTER ROLE %I PASSWORD %L', :'u', :'p') \\gexec",
        "SELECT format('CREATE DATABASE %I OWNER %I', :'d', :'u') WHERE NOT EXISTS "
        "(SELECT 1 FROM pg_database WHERE datname = :'d') \\gexec",
        "",
    ])
    command = ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-p", answers["db_port"], "-d", "postgres"]
    if runner.root:
        command = ["runuser", "-u", "postgres", "--"] + command
    print("\nCreating the database user and database (or updating the password)")
    print("  $ " + " ".join(command) + "   (commands on standard input)")
    if runner.dry_run:
        return
    result = subprocess.run(command, input=script, text=True, capture_output=True, cwd="/")
    if result.returncode != 0:
        raise StepFailed("creating the database", result.stderr)


def whatsapp_key(runner):
    """Start the WhatsApp server and create LKMS's API key. Returns the key, or '' if it could not be made."""
    print("\nStarting the WhatsApp server (the first time takes a few minutes to build)")
    runner.run(["docker", "compose", "up", "-d", "--build", "whatsapp"])
    for attempt in range(4):
        result = runner.run(["docker", "compose", "run", "--rm", "whatsapp", "node", "dist/scripts/lkms-api-key.js"],
                            capture=True, check=False)
        found = re.search(r"WHATSAPP_API_KEY=(\S+)", result.stdout or "")
        if found or runner.dry_run:
            return found.group(1) if found else ""
        time.sleep(10)
    print("  ! Could not create the key:\n" + textwrap.indent((result.stderr or "")[-1500:], "    "))
    return ""


def install(runner):
    backend, frontend = runner.repo / "backend", runner.repo / "frontend"
    uv = shutil.which("uv") or "/usr/local/bin/uv"
    print("\nInstalling LKMS (this takes a few minutes)")
    runner.run([uv, "sync", "--frozen", "--no-dev"], as_app=True, cwd=backend)
    for args in (["migrate"], ["collectstatic", "--noinput"], ["check", "--deploy"]):
        runner.run([".venv/bin/python", "manage.py", *args], as_app=True, cwd=backend)
    runner.run(["npm", "ci", "--no-audit", "--no-fund"], as_app=True, cwd=frontend)
    runner.run(["npm", "run", "build"], as_app=True, cwd=frontend)


def stage_answers(runner, school_file, data_dir):
    """Copy the school's answers file and its pictures where the lkms user can read them."""
    target = Path(data_dir) / "setup"
    print(f"\nCopying {school_file} and its pictures to {target}")
    if runner.dry_run:
        return target / "school.json"
    target.mkdir(parents=True, exist_ok=True)
    os.chmod(target, 0o700)
    chown(target, APP_USER)
    data = json.loads(school_file.read_text())
    for key in ("logo", "upi_qr"):
        if data.get(key):
            source = (school_file.parent / data[key]).resolve()
            shutil.copyfile(source, target / source.name)
            chown(target / source.name, APP_USER)
            data[key] = source.name
    (target / "school.json").write_text(json.dumps(data, indent=2))
    chown(target / "school.json", APP_USER)
    return target / "school.json"


def school_details(runner, answers_file=None):
    command = [".venv/bin/python", "manage.py", "setup_school"]
    if answers_file:
        command += ["--answers", str(answers_file)]
    runner.run(command, as_app=True, cwd=runner.repo / "backend")


def go_live(runner, answers, email):
    domain = answers["domain"]
    deploy = runner.repo / "deploy"
    units = ["lkms-web.service", "lkms-backup.service", "lkms-backup.timer", "lkms-fee-reminders.service",
             "lkms-fee-reminders.timer"]
    if answers["whatsapp"]:
        units.append("lkms-whatsapp-sender.service")
    print("\nTurning on the website, backups and reminders")
    runner.run(["cp", *[str(deploy / unit) for unit in units], "/etc/systemd/system/"])
    runner.run(["systemctl", "daemon-reload"])
    enable = ["lkms-web", "lkms-backup.timer", "lkms-fee-reminders.timer"]
    if answers["whatsapp"]:
        enable.append("lkms-whatsapp-sender")
    runner.run(["systemctl", "enable", "--now", *enable])

    site = Path("/etc/nginx/sites-available/lkms")
    print(f"  writing {site} for {domain}")
    if not runner.dry_run:
        site.write_text((deploy / "nginx-lkms.conf").read_text().replace("school.example.in", domain))
    runner.run(["ln", "-sf", str(site), "/etc/nginx/sites-enabled/lkms"])
    runner.run(["rm", "-f", "/etc/nginx/sites-enabled/default"])
    runner.run(["nginx", "-t"])
    runner.run(["systemctl", "reload", "nginx"])
    runner.run(["certbot", "--nginx", "-d", domain, "--redirect", "-m", email, "--agree-tos", "--non-interactive"])
    runner.run(["systemctl", "start", "lkms-backup.service"])


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ask for LKMS's settings one at a time and set up the server.")
    parser.add_argument("--repo", type=Path, default=DEFAULT_REPO, help="the LKMS folder (default: this copy)")
    parser.add_argument("--dry-run", action="store_true", help="show what would be done without changing anything")
    parser.add_argument("--school", type=Path, help="a school's answers file, e.g. examples/lotus-kids/school.json; "
                                                     "its values are offered as the suggested answers")
    args = parser.parse_args(argv)
    school = {}
    if args.school:
        try:
            school = json.loads(args.school.read_text())
        except (OSError, ValueError) as error:
            print(f"Could not read {args.school}: {error}")
            return 1

    repo = args.repo.resolve()
    backend_env, wa_env = repo / "backend" / ".env", repo / "whatsapp-server" / ".env"
    runner = Runner(repo, args.dry_run)

    say("LKMS setup wizard")
    say("This asks for each setting LKMS needs, one at a time, with a short explanation. Nothing is changed "
        "until you confirm at the end of part 1. Press Ctrl+C at any time to stop.")
    if not runner.root and not args.dry_run:
        say("Note: not running as root, so the database, services and HTTPS steps will be skipped. "
            "Run it with sudo for the full setup.")

    current = read_env(backend_env)
    wa_current = read_env(wa_env) or read_env(repo / "whatsapp-server" / ".env.example")
    answers = ask_settings(current, wa_env.exists(), school)
    summary(answers)
    if not ask_yes("Save these settings?"):
        say("Nothing was saved.")
        return 1

    values = backend_values(answers, current)
    if args.dry_run:
        print(f"\n(dry run) would write {backend_env}")
    else:
        save_env(backend_env, render_env(values, BACKEND_LAYOUT, "LKMS settings"), APP_USER)
        print(f"\nSaved {backend_env} (readable only by {APP_USER}).")
    if answers["whatsapp"]:
        wa_text = render_env(whatsapp_values(wa_current), [], "LKMS WhatsApp server settings")
        if args.dry_run:
            print(f"(dry run) would write {wa_env}")
        else:
            save_env(wa_env, wa_text, APP_USER)
            print(f"Saved {wa_env}.")

    say()
    say("== Part 2 of 2: setting up the server ==")
    say("Each step asks first. Answer n to skip a step you have already done.")
    steps = []
    try:
        if runner.root or args.dry_run:
            create_folders(runner, answers)
            steps.append("folders")
        local_db = answers["db_host"] in ("localhost", "127.0.0.1")
        if (runner.root or args.dry_run) and local_db and shutil.which("psql") and ask_yes(
            "Create the database now (or update its password)?",
            "Needed the first time, and whenever you change the database password above.",
        ):
            create_database(runner, answers)
            steps.append("database")
        if answers["whatsapp"] and not values["WHATSAPP_API_KEY"] and (runner.root or args.dry_run) and ask_yes(
            "Start the WhatsApp server now and connect LKMS to it?",
            "Needs Docker (docs/DEPLOY.md step 3). You will link the school's phone later from the WhatsApp page.",
        ):
            key = whatsapp_key(runner)
            if key:
                values.update(WHATSAPP_API_KEY=key, WHATSAPP_ENABLED="true")
                save_env(backend_env, render_env(values, BACKEND_LAYOUT, "LKMS settings"), APP_USER)
                print("  WhatsApp is connected and switched on in backend/.env.")
                steps.append("WhatsApp server")
            else:
                say("WhatsApp stays off for now. Fix the problem above and run this wizard again.")
        if ask_yes("Install LKMS and prepare the database now?",
                   "Installs the Python and web packages, creates the database tables and builds the website. Run it "
                   "the first time and after changing settings."):
            install(runner)
            steps.append("install")
        if ask_yes("Enter the school's details now (name, logo, classes, subjects, fees, UPI, logins)?",
                   "Another set of questions, one at a time. You can change everything later in the app."):
            answers_file = stage_answers(runner, args.school.resolve(), answers["data_dir"]) if args.school else None
            school_details(runner, answers_file)
            steps.append("school details")
        if (runner.root or args.dry_run) and runner.repo == SERVER_REPO and ask_yes(
            "Turn on the website with HTTPS, nightly backups and fee reminders?",
            f"The DNS of {answers['domain']} must already point at this server, or getting the HTTPS certificate "
            "fails.",
        ):
            email = ask("Email for HTTPS certificate notices?",
                        "Let's Encrypt writes here only if the certificate is about to expire.", check=check_email)
            go_live(runner, answers, email)
            steps.append("website")
    except StepFailed as error:
        print(f"\n  ! This step failed: {error.args[0]}")
        if len(error.args) > 1 and error.args[1]:
            print(textwrap.indent(error.args[1][-2000:], "    "))
        say("Fix the problem and run the wizard again; your answers are saved and will be the defaults.")
        return 1

    say()
    if args.dry_run:
        say("Dry run finished: nothing was changed.")
        return 0
    say("Done: " + (", ".join(steps) if steps else "settings saved") + ".")
    if "website" in steps:
        say(f"Open https://{answers['domain']}/staff/login and sign in as the administrator.")
    say("Keep a copy of backend/.env (and whatsapp-server/.env) somewhere safe off the server.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (KeyboardInterrupt, EOFError):
        print("\nStopped. Anything already saved stays saved; run the wizard again to continue.")
        sys.exit(130)
