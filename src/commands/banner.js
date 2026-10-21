import { SlashCommandBuilder } from 'discord.js';
import { getSmartBanner } from '../services/pinterestService.js';
import { createBannerEmbed, createBannerActionRow } from '../utils/bannerEmbed.js';

export const bannerCommand = {
  data: new SlashCommandBuilder()
    .setName('banner')
    .setDescription('جلب بانر ديسكورد عريض وأفقي من Pinterest')
    .addStringOption(option =>
      option
        .setName('search_term')
        .setDescription('أدخل موضوع البانر (أنمي، ألعاب، جمالي، إلخ)')
        .setRequired(true)
        .setMaxLength(100)
    ),

  async execute(interaction) {
    const searchTerm = interaction.options.getString('search_term', true);
    await interaction.deferReply();

    const bannerData = await getSmartBanner(searchTerm);
    const embed = createBannerEmbed(bannerData, interaction.user);
    const row = createBannerActionRow(searchTerm, interaction.user.id);

    await interaction.editReply({ embeds: [embed], components: [row] });
  }
};
