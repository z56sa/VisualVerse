import { SlashCommandBuilder } from 'discord.js';
import { getSmartGif } from '../services/giphyService.js';
import { createGifEmbed, createGifActionRow } from '../utils/gifEmbed.js';

export const gifCommand = {
  data: new SlashCommandBuilder()
    .setName('gif')
    .setDescription('Search and deliver unlimited GIFs via Giphy with smart fallbacks')
    .addStringOption(option =>
      option
        .setName('search_term')
        .setDescription('Enter a keyword, phrase, or sentence to find the perfect GIF')
        .setRequired(true)
        .setMaxLength(100)
    ),

  /**
   * Executes the /gif slash command
   * @param {import('discord.js').ChatInputCommandInteraction} interaction 
   * @param {string} apiKey 
   */
  async execute(interaction, apiKey) {
    const searchTerm = interaction.options.getString('search_term', true);

    // Defer reply to prevent 3-second interaction timeout on slower network requests
    await interaction.deferReply();

    const gifData = await getSmartGif(apiKey, searchTerm);
    const embed = createGifEmbed(gifData, interaction.user);
    const row = createGifActionRow(searchTerm, interaction.user.id);

    await interaction.editReply({
      embeds: [embed],
      components: [row]
    });
  }
};
