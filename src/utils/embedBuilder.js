import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle
} from 'discord.js';

/**
 * تصميم Embed سينمائي جذاب للأخبار مع الذكاء الاصطناعي
 * @param {Object} param0 
 * @returns {EmbedBuilder}
 */
export function createNewsEmbed({
  arabicTitle,
  originalTitle,
  summaryPoints,
  link,
  imageUrl,
  pubDate,
  sourceName
}) {
  const embed = new EmbedBuilder()
    .setColor(0xFF4500) // لون FeedPulse البرتقالي الناري
    .setTitle(`📰 ${arabicTitle}`)
    .setURL(link)
    .setFooter({
      text: `FeedPulse • ${sourceName || 'مصدر إخباري'}`,
      iconURL: 'https://cdn-icons-png.flaticon.com/512/2965/2965879.png'
    })
    .setTimestamp(pubDate || new Date());

  if (imageUrl) {
    embed.setImage(imageUrl);
  }

  // صياغة الـ 3 نقاط الملخصة
  const formattedSummary = (summaryPoints || [])
    .map(point => `🔹 ${point}`)
    .join('\n\n');

  embed.setDescription(formattedSummary || 'اضغط على زر قراءة التفاصيل للاطلاع على الخبر كاملاً.');

  embed.addFields(
    {
      name: '⏰ توقيت النشر',
      value: `<t:${Math.floor(new Date(pubDate).getTime() / 1000)}:R>`,
      inline: true
    },
    {
      name: '🌐 المصدر',
      value: `**${sourceName || 'RSS Feed'}**`,
      inline: true
    }
  );

  return embed;
}

/**
 * زر تفاعلي ينقل القارئ للمصدر الأصلي
 * @param {string} url 
 * @returns {ActionRowBuilder<ButtonBuilder>}
 */
export function createNewsActionRow(url) {
  const sourceButton = new ButtonBuilder()
    .setLabel('📖 قراءة الخبر كاملاً')
    .setStyle(ButtonStyle.Link)
    .setURL(url);

  return new ActionRowBuilder().addComponents(sourceButton);
}
