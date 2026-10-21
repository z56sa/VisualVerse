import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle
} from 'discord.js';

/**
 * تصميم رسالة Embed لعرض البانر العريض لبروفايل وسيرفر الديسكورد
 * @param {Object} bannerData 
 * @param {import('discord.js').User} user 
 * @returns {EmbedBuilder}
 */
export function createBannerEmbed(bannerData, user) {
  const embed = new EmbedBuilder()
    .setTitle(bannerData.title.length > 250 ? `${bannerData.title.substring(0, 247)}...` : bannerData.title)
    .setURL(bannerData.giphyUrl)
    .setImage(bannerData.url) // يعرض البانر بشكل أفقي عريض
    .setColor(0x5865f2) // لون ديسكورد المميز
    .setFooter({
      text: `Discord Banner (${bannerData.dimensions || 'Wide'}) • Requested by ${user.username}`,
      iconURL: user.displayAvatarURL()
    })
    .setTimestamp();

  if (bannerData.source === 'surprise') {
    embed.setDescription('🎲 **بانر ديسكورد متحرك عشوائي (Random Discord Banner)**');
  } else if (bannerData.source === 'fallback') {
    embed.setDescription(`🎨 **بانر عريض بديل لـ:** \`${bannerData.displayTerm}\``);
  } else {
    embed.setDescription(`🖼️ **بانر ديسكورد عريض لـ:** **${bannerData.displayTerm}**`);
  }

  return embed;
}

/**
 * تشفير معرف الأزرار
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
 * فك تشفير معرف الأزرار
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
 * أزرار التحكم في البانر
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
