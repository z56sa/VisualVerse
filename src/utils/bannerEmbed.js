import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle
} from 'discord.js';

export function createBannerEmbed(bannerData, user) {
  const embed = new EmbedBuilder()
    .setTitle(bannerData.title.length > 250 ? `${bannerData.title.substring(0, 247)}...` : bannerData.title)
    .setURL(bannerData.pinterestUrl || 'https://www.pinterest.com')
    .setImage(bannerData.url)
    .setColor(0xe60023) // لون Pinterest الأحمر
    .setFooter({
      text: `📌 Pinterest Banner (${bannerData.dimensions}) • Requested by ${user.username}`,
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

export function parseBannerCustomId(customId) {
  const parts = customId.split('|');
  return {
    action: parts[0] || '',
    userId: parts[1] || '',
    term: parts.slice(2).join('|') || ''
  };
}

export function buildBannerCustomId(action, term, userId) {
  const cleanTerm = (term || '').replace(/\|/g, '').substring(0, 45);
  return `${action}|${userId}|${cleanTerm}`;
}

export function createBannerActionRow(term, userId) {
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder()
      .setCustomId(buildBannerCustomId('banner_another', term, userId))
      .setLabel('🔄 Another Banner')
      .setStyle(ButtonStyle.Primary),
    new ButtonBuilder()
      .setCustomId(buildBannerCustomId('banner_surprise', term, userId))
      .setLabel('🎲 Surprise Banner')
      .setStyle(ButtonStyle.Secondary),
    new ButtonBuilder()
      .setCustomId(buildBannerCustomId('banner_save', term, userId))
      .setLabel('📌 Save to DM')
      .setStyle(ButtonStyle.Success)
  );
}
