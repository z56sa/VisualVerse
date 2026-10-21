import { EmbedBuilder } from 'discord.js';
import { getSmartBanner, getSurpriseBanner } from '../services/bannerService.js';
import { createBannerEmbed, createBannerActionRow, parseBannerCustomId } from '../utils/bannerEmbed.js';

export async function handleButtonInteraction(interaction, apiKey) {
  const { action, term } = parseBannerCustomId(interaction.customId);

  if (action === 'banner_save') {
    await interaction.deferReply({ flags: 64 });
    try {
      const embed = interaction.message.embeds?.[0];
      if (!embed?.image?.url) {
        await interaction.editReply({ content: '⚠️ لم يتم العثور على صورة لحفظها.' });
        return;
      }
      const dmEmbed = new EmbedBuilder()
        .setTitle(`📌 ${embed.title || 'Discord Banner'}`)
        .setURL(embed.url || 'https://pixabay.com')
        .setImage(embed.image.url)
        .setColor(0x1db954)
        .setDescription(`محفوظ من **${interaction.guild?.name || 'Discord'}** في <#${interaction.channelId}>`)
        .setFooter({ text: 'Discord Banner Bot' })
        .setTimestamp();
      await interaction.user.send({ embeds: [dmEmbed] });
      await interaction.editReply({ content: '✅ تم إرسال البانر إلى رسائلك الخاصة!' });
    } catch {
      await interaction.editReply({ content: '❌ تعذر الإرسال! تأكد من السماح بالرسائل الخاصة.' });
    }
    return;
  }

  if (action === 'banner_another') {
    await interaction.deferUpdate();
    const data = await getSmartBanner(apiKey, term || 'anime');
    await interaction.editReply({
      embeds: [createBannerEmbed(data, interaction.user)],
      components: [createBannerActionRow(term || 'anime', interaction.user.id)]
    });
    return;
  }

  if (action === 'banner_surprise') {
    await interaction.deferUpdate();
    const data = await getSurpriseBanner(apiKey);
    await interaction.editReply({
      embeds: [createBannerEmbed(data, interaction.user)],
      components: [createBannerActionRow('surprise', interaction.user.id)]
    });
    return;
  }
}
