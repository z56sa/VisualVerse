import http from 'http';
import { Client, GatewayIntentBits, Collection } from 'discord.js';
import dotenv from 'dotenv';
import { bannerCommand } from './commands/banner.js';
import { handleButtonInteraction } from './handlers/buttonHandler.js';

dotenv.config();

// ─── Health Check Server for Render ──────────────────────────────────────────
const PORT = process.env.PORT || 3000;
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ status: 'ok', bot: client.user?.tag || 'connecting' }));
});
server.listen(PORT, () => console.log(`🌐 Health check server listening on port ${PORT}`));

// ─── Discord Client ───────────────────────────────────────────────────────────
const { DISCORD_TOKEN } = process.env;

if (!DISCORD_TOKEN) {
  console.error('❌ Missing DISCORD_TOKEN in environment variables!');
  process.exit(1);
}

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages]
});

// Register commands
client.commands = new Collection();
client.commands.set(bannerCommand.data.name, bannerCommand);

// ─── Events ──────────────────────────────────────────────────────────────────
client.once('clientReady', readyClient => {
  console.log(`🤖 Logged in as ${readyClient.user.tag}!`);
  console.log('🌟 Pinterest Animated Banner Bot is ready.');
  readyClient.user.setActivity('/banner [search_term]', { type: 2 });
});

client.on('interactionCreate', async interaction => {
  try {
    if (interaction.isChatInputCommand()) {
      const command = client.commands.get(interaction.commandName);
      if (!command) return;
      await command.execute(interaction);
      return;
    }

    if (interaction.isButton()) {
      await handleButtonInteraction(interaction);
      return;
    }
  } catch (error) {
    console.error('Interaction error:', error);
    const msg = { content: '❌ حدث خطأ أثناء المعالجة، يرجى المحاولة مرة أخرى!', flags: 64 };
    if (interaction.deferred || interaction.replied) {
      await interaction.followUp(msg).catch(() => {});
    } else {
      await interaction.reply(msg).catch(() => {});
    }
  }
});

// ─── Graceful Shutdown ────────────────────────────────────────────────────────
process.on('SIGINT', () => { client.destroy(); process.exit(0); });
process.on('SIGTERM', () => { client.destroy(); process.exit(0); });

// ─── Connect to Discord ───────────────────────────────────────────────────────
client.login(DISCORD_TOKEN).catch(err => {
  console.error('❌ Discord login failed:', err.message);
  process.exit(1);
});
