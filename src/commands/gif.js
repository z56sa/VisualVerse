import { SlashCommandBuilder } from 'discord.js';
import { getSmartGif } from '../services/giphyService.js';
import { createGifEmbed, createGifActionRow } from '../utils/gifEmbed.js';

export const gifCommand = {
  data: new SlashCommandBuilder()
    .setName('gif')
    .setDescription('Search and deliver unlimited animated GIFs via Giphy')
    .addStringOption(option =>
      option
        .setName('search_term')
        .setDescription('Enter any keyword, anime, emotion, or phrase (e.g. anime, cat, dance)')
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
