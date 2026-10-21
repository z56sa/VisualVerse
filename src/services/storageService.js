import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DB_FILE = path.join(__dirname, '..', 'feeds.json');

/**
 * تحميل إعدادات الخلاصات المسجلة
 * {
 *   guildId: {
 *     channelId: "...",
 *     feeds: ["url1", "url2"],
 *     lastPostedIds: ["urlA", "urlB"]
 *   }
 * }
 */
export function loadFeedsConfig() {
  try {
    if (fs.existsSync(DB_FILE)) {
      const data = fs.readFileSync(DB_FILE, 'utf8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error('Error reading feeds.json:', err.message);
  }
  return {};
}

/**
 * حفظ إعدادات الخلاصات
 */
export function saveFeedsConfig(config) {
  try {
    fs.writeFileSync(DB_FILE, JSON.stringify(config, null, 2), 'utf8');
  } catch (err) {
    console.error('Error saving feeds.json:', err.message);
  }
}
