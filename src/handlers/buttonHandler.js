import { EmbedBuilder } from 'discord.js';
import { getSmartBanner, getSurpriseBanner } from '../services/bannerService.js';
import { createBannerEmbed, createBannerActionRow, parseBannerCustomId } from '../utils/bannerEmbed.js';

/**
 * معالج ضغطات الأزرار للبوت (Banner Actions)
 * @param {import('discord.js').ButtonInteraction} interaction 
 * @param {string} apiKey 
 */
export async function handleButtonInteraction(interaction, apiKey) {
  const customId = interaction.customId;
  const { action, term } = parseBannerCustomId(customId);

  // 1. زر حفظ البانر في الخاص (Save to DM)
  if (action === 'banner_save' || action === 'save') {
    await interaction.deferReply({ ephemeral: true });

    try {
      const messageEmbed = interaction.message.embeds?.[0];
      const bannerUrl = messageEmbed?.image?.url;
      const bannerTitle = messageEmbed?.title || 'Saved Animated Banner';

      if (!bannerUrl) {
        await interaction.editReply({
          content: '⚠️ Could not find a banner image in this message to save.'
        });
        return;
      }

      const dmEmbed = new EmbedBuilder()
        .setTitle(`📌 Saved Banner: ${bannerTitle}`)
        .setURL(messageEmbed.url || bannerUrl)
        .setImage(bannerUrl)
        .setColor(0x5865f2)
        .setDescription(`Saved from **${interaction.guild?.name || 'Discord'}** in <#${interaction.channelId}>`)
        .setFooter({ text: 'Saved via Discord Banner Bot' })
        .setTimestamp();

      await interaction.user.send({ embeds: [dmEmbed] });

      await interaction.editReply({
        content: '✅ تم إرسال البانر المتحرك إلى رسائلك الخاصة (DMs) بنجاح!'
      });
    } catch (err) {
      console.warn(`Failed to DM user ${interaction.user.tag}:`, err.message);
      await interaction.editReply({
        content: '❌ تعذر إرسال رسالة خاصة لك! يرجى التأكد من السماح بالرسائل الخاصة في إعدادات خصوصية السيرفر.'
      });
    }
    return;
  }

  // 2. زر جلب بانر آخر لنفس الموضوع (Another Banner)
  if (action === 'banner_another' || action === 'another') {
    await interaction.deferUpdate();

    const targetTerm = term || 'anime';
    const bannerData = await getSmartBanner(apiKey, targetTerm);
    const newEmbed = createBannerEmbed(bannerData, interaction.user);
    const newRow = createBannerActionRow(targetTerm, interaction.user.id);

    await interaction.editReply({
      embeds: [newEmbed],
      components: [newRow]
    });
    return;
  }

  // 3. زر بانر عشوائي مفاجئ (Surprise Banner)
  if (action === 'banner_surprise' || action === 'surprise') {
    await interaction.deferUpdate();

    const bannerData = await getSurpriseBanner(apiKey);
    const newEmbed = createBannerEmbed(bannerData, interaction.user);
    const newRow = createBannerActionRow('surprise', interaction.user.id);

    await interaction.editReply({
      embeds: [newEmbed],
      components: [newRow]
    });
    return;
  }
}
