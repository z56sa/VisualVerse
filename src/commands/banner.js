import { SlashCommandBuilder } from 'discord.js';
import { getSmartBanner } from '../services/bannerService.js';
import { createBannerEmbed, createBannerActionRow } from '../utils/bannerEmbed.js';

export const bannerCommand = {
  data: new SlashCommandBuilder()
    .setName('banner')
    .setDescription('Find and display wide animated Discord landscape banners')
    .addStringOption(option =>
      option
        .setName('search_term')
        .setDescription('Enter a theme, anime, aesthetic, or keyword (e.g. anime, cyberpunk, lofi)')
        .setRequired(true)
        .setMaxLength(100)
    ),

  /**
   * تنفيذ أمر /banner
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
