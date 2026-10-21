import { SlashCommandBuilder } from 'discord.js';
import { getSmartBanner } from '../services/bannerService.js';
import { createBannerEmbed, createBannerActionRow } from '../utils/bannerEmbed.js';

export const bannerCommand = {
  data: new SlashCommandBuilder()
    .setName('banner')
    .setDescription('Find and display wide animated landscape banners using Giphy')
    .addStringOption(option =>
      option
        .setName('search_term')
        .setDescription('Enter a theme, anime, aesthetic, or keyword (e.g. cyberpunk, lofi, naruto)')
        .setRequired(true)
        .setMaxLength(100)
    ),

  /**
   * Executes the /banner slash command
   * @param {import('discord.js').ChatInputCommandInteraction} interaction 
   * @param {string} apiKey 
   */
  async execute(interaction, apiKey) {
    const searchTerm = interaction.options.getString('search_term', true);

    await interaction.deferReply();

    const bannerData = await getSmartBanner(apiKey, searchTerm);
    const embed = createBannerEmbed(bannerData, interaction.user);
    const row = createBannerActionRow(searchTerm, interaction.user.id);

    await interaction.editReply({
      embeds: [embed],
      components: [row]
    });
  }
};
