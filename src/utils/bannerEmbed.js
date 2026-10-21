import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle
} from 'discord.js';

/**
 * Creates the Discord Embed tailored to showcase wide animated banners
 * @param {Object} bannerData 
 * @param {import('discord.js').User} user 
 * @returns {EmbedBuilder}
 */
export function createBannerEmbed(bannerData, user) {
  const embed = new EmbedBuilder()
    .setTitle(bannerData.title.length > 250 ? `${bannerData.title.substring(0, 247)}...` : bannerData.title)
    .setURL(bannerData.giphyUrl)
    .setImage(bannerData.url) // Sets the banner as the prominent main image
    .setColor(0x5865f2) // Discord Blurple
    .setFooter({
      text: `Animated Banner • Requested by ${user.username}`,
      iconURL: user.displayAvatarURL()
    })
    .setTimestamp();

  if (bannerData.source === 'surprise') {
    embed.setDescription('🎲 *Surprise Animated Landscape Banner*');
  } else if (bannerData.source === 'fallback') {
    embed.setDescription(`*No exact banner matches for \`${bannerData.displayTerm}\`. Showing an aesthetic wide banner!*`);
  } else {
    embed.setDescription(`🎨 *Animated Banner for:* **${bannerData.displayTerm}**`);
  }

  return embed;
}

/**
 * Encodes button customId safely within Discord's 100 char limit
 * @param {string} action - 'banner_another', 'banner_surprise', 'banner_save'
 * @param {string} term 
 * @param {string} userId 
 * @returns {string}
 */
export function buildBannerCustomId(action, term, userId) {
  const cleanTerm = (term || '').replace(/\|/g, '').substring(0, 45);
  return `${action}|${userId}|${cleanTerm}`;
}

/**
 * Parses customId string
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
 * Creates interactive action buttons for the banner response
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
    .setLabel('📌 Save')
    .setStyle(ButtonStyle.Success);

  return new ActionRowBuilder().addComponents(anotherButton, surpriseButton, saveButton);
}
