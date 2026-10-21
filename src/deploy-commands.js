import { REST, Routes } from 'discord.js';
import dotenv from 'dotenv';
import matchingCommand from './commands/matching.js';
import getMediaCommand from './commands/get-media.js';
import downloadVideoCommand from './commands/download-video.js';
import adminPairCommand from './commands/admin-pair.js';

dotenv.config();

const commands = [
  matchingCommand.data.toJSON(),
  getMediaCommand.data.toJSON(),
  downloadVideoCommand.data.toJSON(),
  adminPairCommand.data.toJSON()
];

const token = process.env.DISCORD_TOKEN;
const clientId = process.env.CLIENT_ID;
const guildId = process.env.GUILD_ID;

if (!token || !clientId) {
  console.error('❌ خطأ: يرجى التحقق من توفر DISCORD_TOKEN و CLIENT_ID داخل ملف .env');
  process.exit(1);
}

const rest = new REST({ version: '10' }).setToken(token);

(async () => {
  try {
    console.log(`🚀 جاري تسجيل ${commands.length} أمر من أوامر السلاش (Slash Commands)...`);

    if (guildId && guildId.trim() !== '') {
      // Fast registration to a specific server
      await rest.put(
        Routes.applicationGuildCommands(clientId, guildId.trim()),
        { body: commands }
      );
      console.log(`✅ تم نشر وتحديث الأوامر بنجاح على السيرفر الخاص: ${guildId}`);
    } else {
      // Global registration (across all Discord servers)
      await rest.put(
        Routes.applicationCommands(clientId),
        { body: commands }
      );
      console.log('✅ تم نشر وتحديث الأوامر بنجاح عالمياً (Global Commands)');
    }
  } catch (error) {
    console.error('❌ حدث خطأ أثناء نشر الأوامر:', error);
  }
})();
