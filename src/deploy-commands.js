import { REST, Routes } from 'discord.js';
import dotenv from 'dotenv';
import { gifCommand } from './commands/gif.js';

dotenv.config();

const { DISCORD_TOKEN, CLIENT_ID, GUILD_ID } = process.env;

if (!DISCORD_TOKEN || !CLIENT_ID) {
  console.error('❌ Error: DISCORD_TOKEN and CLIENT_ID are required in .env');
  process.exit(1);
}

// Commands focused purely on GIFs
const commands = [gifCommand.data.toJSON()];
const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);

async function deploy() {
  try {
    console.log(`🚀 Refreshing ${commands.length} application (/) commands...`);

    if (GUILD_ID && GUILD_ID.trim().length > 0) {
      console.log(`🎯 Registering slash commands specifically to Guild ID: ${GUILD_ID}`);
      await rest.put(
        Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID.trim()),
        { body: commands }
      );
    } else {
      console.log('🌐 Registering slash commands globally...');
      await rest.put(
        Routes.applicationCommands(CLIENT_ID),
        { body: commands }
      );
    }

    console.log('✅ Application (/) commands registered successfully!');
  } catch (error) {
    console.error('❌ Failed to register commands:', error);
    process.exit(1);
  }
}

deploy();
