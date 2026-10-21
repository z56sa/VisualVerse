import {
  Client,
  GatewayIntentBits,
  Collection,
  ActivityType,
  Events,
  MessageFlags
} from 'discord.js';
import dotenv from 'dotenv';
import http from 'http';

// Services & Utils
import dbService from './services/database.js';
import embedUtils from './utils/embedBuilder.js';

// Commands
import matchingCommand from './commands/matching.js';
import getMediaCommand from './commands/get-media.js';
import downloadVideoCommand from './commands/download-video.js';
import adminPairCommand from './commands/admin-pair.js';

dotenv.config();

// Initialize Discord Client
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.GuildMembers
  ]
});

// Setup Commands Collection
client.commands = new Collection();
client.commands.set(matchingCommand.data.name, matchingCommand);
client.commands.set(getMediaCommand.data.name, getMediaCommand);
client.commands.set(downloadVideoCommand.data.name, downloadVideoCommand);
client.commands.set(adminPairCommand.data.name, adminPairCommand);

// Bot Ready Event
client.once(Events.ClientReady, (c) => {
  console.log(`===============================================`);
  console.log(`🤖 بوت VisualVerse متصل الآن بنجاح!`);
  console.log(`👤 مسجل باسم: ${c.user.tag}`);
  console.log(`🌐 متواجد في: ${c.guilds.cache.size} سيرفر`);
  console.log(`===============================================`);

  // Set rich presence
  c.user.setPresence({
    activities: [
      {
        name: '/matching | Avatars & Banners 🎨',
        type: ActivityType.Watching
      }
    ],
    status: 'online'
  });
});

// Interaction Handling (Slash Commands & Interactive Buttons)
client.on(Events.InteractionCreate, async (interaction) => {
  try {
    // 1. Handle Slash Commands
    if (interaction.isChatInputCommand()) {
      const command = client.commands.get(interaction.commandName);

      if (!command) {
        console.warn(`الأمر ${interaction.commandName} غير مسجل.`);
        return;
      }

      await command.execute(interaction);
      return;
    }

    // 2. Handle Button Clicks
    if (interaction.isButton()) {
      const customId = interaction.customId;

      // Handle "Next Image 🔄" button
      if (customId.startsWith('matching_next_')) {
        const category = customId.replace('matching_next_', '');
        await interaction.deferUpdate();

        const pair = dbService.getRandomPair(category);

        if (!pair) {
          return interaction.followUp({
            content: '⚠️ لا توجد صور متوفرة في هذه الفئة حالياً.',
            flags: MessageFlags.Ephemeral
          });
        }

        const { embed, row } = embedUtils.createMatchingPairEmbed(pair, interaction.user);

        return await interaction.editReply({
          embeds: [embed],
          components: [row]
        });
      }

      // Handle "Send to DM 📩" button
      if (customId.startsWith('matching_dm_')) {
        const pairId = parseInt(customId.replace('matching_dm_', ''), 10);
        await interaction.deferReply({ flags: MessageFlags.Ephemeral });

        const pair = dbService.getPairById(pairId);

        if (!pair) {
          return interaction.editReply({
            content: '❌ تعذر العثور على هذا الثنائي، ربما تم حذفه.'
          });
        }

        try {
          const { embed } = embedUtils.createMatchingPairEmbed(pair, interaction.user);
          await interaction.user.send({
            content: '📬 **إليك الثنائي المتطابق الذي قمت بطلبه:**',
            embeds: [embed]
          });

          return interaction.editReply({
            content: '✅ تم إرسال الافتار والبنر إلى رسائلك الخاصة (DM) بنجاح!'
          });
        } catch (dmErr) {
          return interaction.editReply({
            content: '❌ تعذر إرسال الرسالة إلى الخاص. تأكد من فتح الرسائل المباشرة (Direct Messages) في إعدادات الخصوصية.'
          });
        }
      }
    }
  } catch (err) {
    console.error('Error handling interaction:', err);

    const errorMessage = {
      content: '❌ حدث خطأ غير متوقع أثناء معالجة هذا الإجراء!',
      flags: MessageFlags.Ephemeral
    };

    if (interaction.replied || interaction.deferred) {
      await interaction.followUp(errorMessage).catch(() => {});
    } else {
      await interaction.reply(errorMessage).catch(() => {});
    }
  }
});

// Simple HTTP Health-Check Server (For free cloud platforms like Render / Railway / Replit)
const PORT = process.env.PORT || 3000;
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify({
    status: 'online',
    bot: client.user ? client.user.tag : 'Connecting...',
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  }));
});

server.listen(PORT, () => {
  console.log(`🌐 سيرفر المراقبة الحية (Health Check) يعمل على المنفذ: ${PORT}`);
});

// Global Error Catchers
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught Exception thrown:', err);
});

// Login Bot
if (process.env.DISCORD_TOKEN) {
  client.login(process.env.DISCORD_TOKEN).catch((err) => {
    console.error('❌ فشل تسجيل دخول البوت. تأكد من DISCORD_TOKEN:', err.message);
  });
} else {
  console.warn('⚠️ لم يتم العثور على DISCORD_TOKEN في ملف .env!');
}
