import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle
} from 'discord.js';

/**
 * Creates the Discord Embed displaying the GIF
 * @param {Object} gifData 
 * @param {import('discord.js').User} user 
 * @returns {EmbedBuilder}
 */
export function createGifEmbed(gifData, user) {
  const embed = new EmbedBuilder()
    .setTitle(gifData.title.length > 250 ? `${gifData.title.substring(0, 247)}...` : gifData.title)
    .setURL(gifData.giphyUrl)
    .setImage(gifData.url)
    .setColor(0x00ff99) // Giphy vibrant green
    .setFooter({
      text: `Powered by GIPHY • Requested by ${user.username}`,
      iconURL: user.displayAvatarURL()
    })
    .setTimestamp();

  if (gifData.source === 'fallback') {
    embed.setDescription(`*No direct matches for \`${gifData.displayTerm}\`. Showing a related reaction GIF!*`);
  } else if (gifData.source === 'trending') {
    embed.setDescription('🔥 *Currently Trending GIF*');
  } else {
    embed.setDescription(`🎬 *GIF for:* **${gifData.displayTerm}**`);
  }

  return embed;
}

/**
 * Encodes state into button customId safely
 * @param {string} action - 'another', 'surprise', 'save'
 * @param {string} term 
 * @param {string} userId 
 * @returns {string}
 */
export function buildCustomId(action, term, userId) {
  const sanitizedTerm = (term || '').replace(/\|/g, '').substring(0, 50);
  return `${action}|${userId}|${sanitizedTerm}`;
}

/**
 * Parses customId string back to components
 * @param {string} customId 
 * @returns {{ action: string, userId: string, term: string }}
 */
export function parseCustomId(customId) {
  const parts = customId.split('|');
  return {
    action: parts[0] || '',
    userId: parts[1] || '',
    term: parts.slice(2).join('|') || ''
  };
}

/**
 * Creates interactive action buttons for the GIF response
 * @param {string} term 
 * @param {string} userId 
 * @returns {ActionRowBuilder<ButtonBuilder>}
 */
export function createGifActionRow(term, userId) {
  const anotherButton = new ButtonBuilder()
    .setCustomId(buildCustomId('another', term, userId))
    .setLabel('🔄 Another One')
    .setStyle(ButtonStyle.Primary);

  const surpriseButton = new ButtonBuilder()
    .setCustomId(buildCustomId('surprise', term, userId))
    .setLabel('🎲 Surprise Me')
    .setStyle(ButtonStyle.Secondary);

  const saveButton = new ButtonBuilder()
    .setCustomId(buildCustomId('save', term, userId))
    .setLabel('📌 Save to DM')
    .setStyle(ButtonStyle.Success);

  return new ActionRowBuilder().addComponents(anotherButton, surpriseButton, saveButton);
}
