import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle
} from 'discord.js';

/**
 * بناء رسالة Embed مخصصة بالكامل لاستعراض البانر الأفقي العريض
 * @param {Object} bannerData 
 * @param {import('discord.js').User} user 
 * @returns {EmbedBuilder}
 */
export function createBannerEmbed(bannerData, user) {
  const embed = new EmbedBuilder()
    .setTitle(bannerData.title.length > 250 ? `${bannerData.title.substring(0, 247)}...` : bannerData.title)
    .setURL(bannerData.giphyUrl)
    .setImage(bannerData.url) // يعرض البانر العريض في المنتصف بحجم كامل
    .setColor(0x5865f2) // لون ديسكورد المميز (Blurple)
    .setFooter({
      text: `Discord Banner (${bannerData.dimensions || 'Wide'}) • Requested by ${user.username}`,
      iconURL: user.displayAvatarURL()
    })
    .setTimestamp();

  if (bannerData.source === 'surprise') {
    embed.setDescription('🎲 **بانر عريض عشوائي (Discord Profile / Server Banner)**');
  } else if (bannerData.source === 'fallback') {
    embed.setDescription(`🎨 **بانر عريض بديل لـ:** \`${bannerData.displayTerm}\``);
  } else {
    embed.setDescription(`🖼️ **بانر ديسكورد متحرك لـ:** **${bannerData.displayTerm}**`);
  }

  return embed;
}

/**
 * تشفير المعرف المخصص للأزرار بأمان تحت حد 100 حرف
 * @param {string} action 
 * @param {string} term 
 * @param {string} userId 
 * @returns {string}
 */
export function buildBannerCustomId(action, term, userId) {
  const cleanTerm = (term || '').replace(/\|/g, '').substring(0, 45);
  return `${action}|${userId}|${cleanTerm}`;
}

/**
 * فك تشفير المعرف المخصص
 * @param {string} customId 
 * @returns {{ action: string, userId: string, term: string }}
 */
export function parseBannerCustomId(customId) {
  const parts = customId.split('|');
  return {
    action: parts[0] || '',
    userId: parts[1] || '',
    term: parts.slice(2).join('|') || ''
  };
}

/**
 * إنشاء أزرار التحكم الخاصة بالبانرات
 * @param {string} term 
 * @param {string} userId 
 * @returns {ActionRowBuilder<ButtonBuilder>}
 */
export function createBannerActionRow(term, userId) {
  const anotherButton = new ButtonBuilder()
    .setCustomId(buildBannerCustomId('banner_another', term, userId))
    .setLabel('🔄 Another Banner')
    .setStyle(ButtonStyle.Primary);

  const surpriseButton = new ButtonBuilder()
    .setCustomId(buildBannerCustomId('banner_surprise', term, userId))
    .setLabel('🎲 Surprise Banner')
    .setStyle(ButtonStyle.Secondary);

  const saveButton = new ButtonBuilder()
    .setCustomId(buildBannerCustomId('banner_save', term, userId))
    .setLabel('📌 Save to DM')
    .setStyle(ButtonStyle.Success);

  return new ActionRowBuilder().addComponents(anotherButton, surpriseButton, saveButton);
}
