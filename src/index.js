import http from 'http';
import { Client, GatewayIntentBits, Collection } from 'discord.js';
import dotenv from 'dotenv';
import { gifCommand } from './commands/gif.js';
import { handleButtonInteraction } from './handlers/buttonHandler.js';

dotenv.config();

// Web Server for Render Web Service (binds to process.env.PORT to satisfy health checks)
const PORT = process.env.PORT || 3000;
const server = http.createServer((req, res) => {
  if (req.url === '/' || req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', bot: client.user ? client.user.tag : 'connecting' }));
  } else {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not Found');
  }
});

server.listen(PORT, () => {
  console.log(`🌐 Health check server listening on port ${PORT}`);
});

const { DISCORD_TOKEN, GIPHY_API_KEY } = process.env;

if (!DISCORD_TOKEN) {
  console.error('❌ Missing DISCORD_TOKEN in .env file!');
  process.exit(1);
}

if (!GIPHY_API_KEY) {
  console.warn('⚠️ Warning: GIPHY_API_KEY is not set or empty in .env. Bot will use fallback mode.');
}

// Initialize Discord Client with appropriate intents
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.DirectMessages
  ]
});

// Setup commands collection
client.commands = new Collection();
client.commands.set(gifCommand.data.name, gifCommand);

// Ready event
client.once('ready', (readyClient) => {
  console.log(`🤖 Logged in as ${readyClient.user.tag}!`);
  console.log(`🌟 GIF Bot ready to serve unlimited GIFs.`);
  readyClient.user.setActivity('/gif [search_term]', { type: 2 }); // Listening to /gif
});

// Interaction listener
client.on('interactionCreate', async (interaction) => {
  try {
    // 1. Slash Command Handling
    if (interaction.isChatInputCommand()) {
      const command = client.commands.get(interaction.commandName);
      if (!command) {
        console.warn(`No command matching ${interaction.commandName} was found.`);
        return;
      }

      await command.execute(interaction, GIPHY_API_KEY);
      return;
    }

    // 2. Button Component Handling
    if (interaction.isButton()) {
      await handleButtonInteraction(interaction, GIPHY_API_KEY);
      return;
    }
  } catch (error) {
    console.error('Error handling interaction:', error);

    const errorMessage = {
      content: '❌ There was an error while processing your request. Please try again!',
      ephemeral: true
    };

    if (interaction.deferred || interaction.replied) {
      await interaction.followUp(errorMessage).catch(() => {});
    } else {
      await interaction.reply(errorMessage).catch(() => {});
    }
  }
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nShutting down bot gracefully...');
  client.destroy();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\nTerminating bot gracefully...');
  client.destroy();
  process.exit(0);
});

// Connect bot to Discord
client.login(DISCORD_TOKEN).catch((err) => {
  console.error('❌ Discord connection failed:', err.message);
  process.exit(1);
});
