import http from 'http';
import { Client, GatewayIntentBits, Collection } from 'discord.js';
import dotenv from 'dotenv';
import { bannerCommand } from './commands/banner.js';
import { handleButtonInteraction } from './handlers/buttonHandler.js';

dotenv.config();

const PORT = process.env.PORT || 3000;
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ status: 'ok', bot: client.user?.tag || 'connecting' }));
});
server.listen(PORT, () => console.log(`🌐 Health check server on port ${PORT}`));

const { DISCORD_TOKEN, PIXABAY_API_KEY } = process.env;

if (!DISCORD_TOKEN) {
  console.error('❌ Missing DISCORD_TOKEN!');
  process.exit(1);
}
if (!PIXABAY_API_KEY) {
  console.warn('⚠️ PIXABAY_API_KEY is not set! Banners may not load.');
}

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages]
});

client.commands = new Collection();
client.commands.set(bannerCommand.data.name, bannerCommand);

client.once('clientReady', readyClient => {
  console.log(`🤖 Logged in as ${readyClient.user.tag}!`);
  console.log('🌟 Discord Animated Banner Bot ready.');
  readyClient.user.setActivity('/banner [search_term]', { type: 2 });
});

client.on('interactionCreate', async interaction => {
  try {
    if (interaction.isChatInputCommand()) {
      const command = client.commands.get(interaction.commandName);
      if (!command) return;
      await command.execute(interaction, PIXABAY_API_KEY);
      return;
    }
    if (interaction.isButton()) {
      await handleButtonInteraction(interaction, PIXABAY_API_KEY);
    }
  } catch (error) {
    console.error('Interaction error:', error);
    const msg = { content: '❌ حدث خطأ، يرجى المحاولة مرة أخرى!', flags: 64 };
    if (interaction.deferred || interaction.replied) {
      await interaction.followUp(msg).catch(() => {});
    } else {
      await interaction.reply(msg).catch(() => {});
    }
  }
});

process.on('SIGINT', () => { client.destroy(); process.exit(0); });
process.on('SIGTERM', () => { client.destroy(); process.exit(0); });

client.login(DISCORD_TOKEN).catch(err => {
  console.error('❌ Discord login failed:', err.message);
  process.exit(1);
});
