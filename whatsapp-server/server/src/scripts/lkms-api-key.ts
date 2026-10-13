/**
 * LKMS: create the API key the school system uses to send WhatsApp messages.
 *
 * Creates the admin user from ADMIN_USERNAME / ADMIN_PASSWORD if it does not
 * exist, then a new API key owned by that user, and prints the key once.
 * Put the printed key in backend/.env as WHATSAPP_API_KEY.
 *
 *   docker compose run --rm whatsapp node dist/scripts/lkms-api-key.js
 */
import crypto from 'crypto';
import { connectDatabase, disconnectDatabase } from '../config/database';
import { env } from '../config/env';
import { ApiKey } from '../models/ApiKey';
import { User } from '../models/User';
import { hashToken } from '../utils/crypto';

async function main() {
  await connectDatabase();
  let admin = await User.findOne({ username: env.ADMIN_USERNAME });
  if (!admin) {
    admin = new User({ username: env.ADMIN_USERNAME, password: env.ADMIN_PASSWORD, role: 'admin', isActive: true });
    await admin.save();
  }
  const rawKey = 'wa_' + crypto.randomBytes(24).toString('hex');
  await ApiKey.create({ name: `lkms-${new Date().toISOString().slice(0, 10)}`, key: rawKey, keyHash: hashToken(rawKey), userId: admin._id });
  // eslint-disable-next-line no-console
  console.log(`\nWHATSAPP_API_KEY=${rawKey}\n\nCopy this line into backend/.env. It is not shown again.`);
  await disconnectDatabase();
}

main().catch((err) => {
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});
