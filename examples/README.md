# Example answers files

Ready answers for the setup wizard, one folder per school. See `docs/NEW_SCHOOL.md` for every key.

- `lotus-kids/` – Lotus Kids School (Rajasthan board), with its UPI QR code. The address, phone and real fee
  amounts are left out, so the wizard asks for them.
- `green-valley/` – a made-up CBSE school that uses every key, for demos and tests.

Copy a folder for a new school, edit `school.json`, then run
`sudo python3 /srv/lkms/deploy/setup_wizard.py --school /path/to/school.json`.
