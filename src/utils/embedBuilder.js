import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle
} from 'discord.js';

/**
 * تصميم Embed سينمائي جذاب للأخبار مع دعم اللغتين
 * @param {Object} param0 
 * @returns {EmbedBuilder}
 */
export function createNewsEmbed({
  title,
  summaryPoints,
  link,
  imageUrl,
  pubDate,
  sourceName,
  lang = 'ar'
}) {
  const isArabic = lang === 'ar';

  const embed = new EmbedBuilder()
    .setColor(0xFF4500) // لون FeedPulse البرتقالي
    .setTitle(`📰 ${title}`)
    .setURL(link)
    .setFooter({
      text: isArabic ? `FeedPulse • ${sourceName || 'مصدر إخباري'}` : `FeedPulse • ${sourceName || 'News Source'}`,
      iconURL: 'https://cdn-icons-png.flaticon.com/512/2965/2965879.png'
    })
    .setTimestamp(pubDate || new Date());

  if (imageUrl) {
    embed.setImage(imageUrl);
  }

  const formattedSummary = (summaryPoints || [])
    .map(point => `🔹 ${point}`)
    .join('\n\n');

  embed.setDescription(formattedSummary || (isArabic ? 'اضغط على زر قراءة التفاصيل للاطلاع على الخبر كاملاً.' : 'Click below to read the full report.'));

  embed.addFields(
    {
      name: isArabic ? '⏰ توقيت النشر' : '⏰ Published',
      value: `<t:${Math.floor(new Date(pubDate).getTime() / 1000)}:R>`,
      inline: true
    },
    {
      name: isArabic ? '🌐 المصدر' : '🌐 Source',
      value: `**${sourceName || 'RSS Feed'}**`,
      inline: true
    }
  );

  return embed;
}

/**
 * زر تفاعلي ينقل القارئ للمصدر الأصلي
 * @param {string} url 
 * @param {'ar' | 'en'} lang 
 * @returns {ActionRowBuilder<ButtonBuilder>}
 */
export function createNewsActionRow(url, lang = 'ar') {
  const isArabic = lang === 'ar';
  const sourceButton = new ButtonBuilder()
    .setLabel(isArabic ? '📖 قراءة الخبر كاملاً' : '📖 Read Full Story')
    .setStyle(ButtonStyle.Link)
    .setURL(url);

  return new ActionRowBuilder().addComponents(sourceButton);
}
