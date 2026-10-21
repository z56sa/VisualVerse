import { EmbedBuilder } from 'discord.js';
import { getSmartBanner, getSurpriseBanner } from '../services/pinterestService.js';
import { createBannerEmbed, createBannerActionRow, parseBannerCustomId } from '../utils/bannerEmbed.js';

export async function handleButtonInteraction(interaction) {
  const { action, term } = parseBannerCustomId(interaction.customId);

  // 📌 حفظ البانر في DM
  if (action === 'banner_save') {
    await interaction.deferReply({ flags: 64 }); // ephemeral flag

    try {
      const messageEmbed = interaction.message.embeds?.[0];
      const bannerUrl = messageEmbed?.image?.url;

      if (!bannerUrl) {
        await interaction.editReply({ content: '⚠️ لم يتم العثور على صورة لحفظها.' });
        return;
      }

      const dmEmbed = new EmbedBuilder()
        .setTitle(`📌 ${messageEmbed.title || 'Discord Banner'}`)
        .setURL(messageEmbed.url || 'https://www.pinterest.com')
        .setImage(bannerUrl)
        .setColor(0xe60023)
        .setDescription(`محفوظ من **${interaction.guild?.name || 'Discord'}** في <#${interaction.channelId}>`)
        .setFooter({ text: 'Pinterest Banner Bot' })
        .setTimestamp();

      await interaction.user.send({ embeds: [dmEmbed] });
      await interaction.editReply({ content: '✅ تم إرسال البانر إلى رسائلك الخاصة!' });
    } catch (err) {
      await interaction.editReply({
        content: '❌ تعذر الإرسال! تأكد من السماح بالرسائل الخاصة في إعدادات الخصوصية.'
      });
    }
    return;
  }

  // 🔄 بانر آخر لنفس الكلمة
  if (action === 'banner_another') {
    await interaction.deferUpdate();
    const bannerData = await getSmartBanner(term || 'anime');
    await interaction.editReply({
      embeds: [createBannerEmbed(bannerData, interaction.user)],
      components: [createBannerActionRow(term || 'anime', interaction.user.id)]
    });
    return;
  }

  // 🎲 بانر عشوائي مفاجئ
  if (action === 'banner_surprise') {
    await interaction.deferUpdate();
    const bannerData = await getSurpriseBanner();
    await interaction.editReply({
      embeds: [createBannerEmbed(bannerData, interaction.user)],
      components: [createBannerActionRow('surprise', interaction.user.id)]
    });
    return;
  }
}
