import { REST, Routes } from 'discord.js';
import dotenv from 'dotenv';
import { setupFeedCommand } from './commands/setup-feed.js';
import { latestNewsCommand } from './commands/latest-news.js';
import { dailyRecapCommand } from './commands/daily-recap.js';

dotenv.config();

const { DISCORD_TOKEN, CLIENT_ID, GUILD_ID } = process.env;

if (!DISCORD_TOKEN || !CLIENT_ID) {
  console.error('❌ Error: DISCORD_TOKEN and CLIENT_ID are required in .env');
  process.exit(1);
}

const commands = [
  setupFeedCommand.data.toJSON(),
  latestNewsCommand.data.toJSON(),
  dailyRecapCommand.data.toJSON()
];

const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);

async function deploy() {
  try {
    console.log(`🚀 FeedPulse: Registering ${commands.length} application (/) commands...`);

    if (GUILD_ID && GUILD_ID.trim().length > 0) {
      console.log(`🎯 Registering commands to Guild: ${GUILD_ID}`);
      await rest.put(
        Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID.trim()),
        { body: commands }
      );
    } else {
      console.log('🌐 Registering commands globally across all Discord servers...');
      await rest.put(
        Routes.applicationCommands(CLIENT_ID),
        { body: commands }
      );
    }

    console.log('✅ FeedPulse application (/) commands registered successfully!');
  } catch (error) {
    console.error('❌ Failed to register commands:', error);
    process.exit(1);
  }
}

deploy();
