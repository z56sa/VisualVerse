import { REST, Routes } from 'discord.js';
import { SlashCommandBuilder } from 'discord.js';
import dotenv from 'dotenv';
dotenv.config();

const { DISCORD_TOKEN, CLIENT_ID, GUILD_ID } = process.env;
if (!DISCORD_TOKEN || !CLIENT_ID) { console.error('❌ Missing credentials'); process.exit(1); }

const commands = [
  new SlashCommandBuilder()
    .setName('banner')
    .setDescription('جلب بانر ديسكورد عريض من Pinterest')
    .addStringOption(opt =>
      opt.setName('search_term').setDescription('أدخل الموضوع (anime, lofi, cyberpunk...)').setRequired(true).setMaxLength(100)
    ).toJSON()
];

const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);
(async () => {
  try {
    console.log('🚀 Registering commands...');
    if (GUILD_ID?.trim()) {
      await rest.put(Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID.trim()), { body: commands });
    } else {
      await rest.put(Routes.applicationCommands(CLIENT_ID), { body: commands });
    }
    console.log('✅ Commands registered successfully!');
  } catch (e) { console.error('❌', e); process.exit(1); }
})();
