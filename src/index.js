import http from 'http';
import { Client, GatewayIntentBits, Collection } from 'discord.js';
import dotenv from 'dotenv';
import { setupFeedCommand } from './commands/setup-feed.js';
import { latestNewsCommand } from './commands/latest-news.js';
import { dailyRecapCommand } from './commands/daily-recap.js';
import { setLanguageCommand } from './commands/set-language.js';
import { checkFeedsAndBroadcast } from './services/autoFeedService.js';

dotenv.config();

// ─── Health Check Server for Render ──────────────────────────────────────────
const PORT = process.env.PORT || 3000;
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({
    status: 'ok',
    bot: client.user?.tag || 'connecting',
    service: 'FeedPulse AI News Aggregator'
  }));
});
server.listen(PORT, () => console.log(`🌐 FeedPulse Health check server running on port ${PORT}`));

// ─── Environment Variables ────────────────────────────────────────────────────
const { DISCORD_TOKEN, GEMINI_API_KEY } = process.env;

if (!DISCORD_TOKEN) {
  console.error('❌ Missing DISCORD_TOKEN in environment variables!');
  process.exit(1);
}

if (!GEMINI_API_KEY) {
  console.warn('⚠️ Warning: GEMINI_API_KEY is not set. Bot will use built-in smart summarizer fallback.');
}

// ─── Discord Client Setup ────────────────────────────────────────────────────
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages
  ]
});

// Setup Commands Collection
client.commands = new Collection();
client.commands.set(setupFeedCommand.data.name, setupFeedCommand);
client.commands.set(latestNewsCommand.data.name, latestNewsCommand);
client.commands.set(dailyRecapCommand.data.name, dailyRecapCommand);
client.commands.set(setLanguageCommand.data.name, setLanguageCommand);

// ─── Ready Event & Background Poller ─────────────────────────────────────────
client.once('clientReady', async readyClient => {
  console.log(`🤖 Logged in as ${readyClient.user.tag}!`);
  console.log('⚡ FeedPulse AI News Aggregator Bot is active & running.');
  readyClient.user.setActivity('📰 تلخيص الأخبار بالذكاء الاصطناعي', { type: 3 }); // Watching

  // تسجيل وتحديث الـ Slash Commands تلقائياً ومباشرة عبر البوت نفسه فور تشغيله
  try {
    console.log('🔄 Auto-registering Slash Commands directly via Client...');
    const commandsData = [
      setupFeedCommand.data.toJSON(),
      latestNewsCommand.data.toJSON(),
      dailyRecapCommand.data.toJSON(),
      setLanguageCommand.data.toJSON()
    ];
    await readyClient.application.commands.set(commandsData);
    console.log('✅ All Slash Commands registered successfully with Discord API!');
  } catch (regError) {
    console.error('⚠️ Could not auto-register commands via client:', regError.message);
  }

  // فحص الخلاصات التلقائي فور تشغيل البوت
  checkFeedsAndBroadcast(client, GEMINI_API_KEY);

  // فحص دوري تلقائي كل 10 دقائق للأخبار الجديدة
  const POLL_INTERVAL = 10 * 60 * 1000;
  setInterval(() => {
    checkFeedsAndBroadcast(client, GEMINI_API_KEY);
  }, POLL_INTERVAL);
});

// ─── Interaction Listener ────────────────────────────────────────────────────
client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;

  const command = client.commands.get(interaction.commandName);
  if (!command) return;

  try {
    await command.execute(interaction, GEMINI_API_KEY);
  } catch (error) {
    console.error(`Error executing ${interaction.commandName}:`, error);
    const errorMessage = {
      content: '❌ حدث خطأ أثناء تنفيذ هذا الأمر، يرجى المحاولة لاحقاً!',
      ephemeral: true
    };

    if (interaction.deferred || interaction.replied) {
      await interaction.followUp(errorMessage).catch(() => {});
    } else {
      await interaction.reply(errorMessage).catch(() => {});
    }
  }
});

// ─── Graceful Shutdown ────────────────────────────────────────────────────────
process.on('SIGINT', () => {
  console.log('Shutting down FeedPulse gracefully...');
  client.destroy();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('Terminating FeedPulse gracefully...');
  client.destroy();
  process.exit(0);
});

// ─── Connect to Discord ───────────────────────────────────────────────────────
client.login(DISCORD_TOKEN).catch(err => {
  console.error('❌ Discord connection failed:', err.message);
  process.exit(1);
});
