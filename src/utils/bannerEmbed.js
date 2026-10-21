import {
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle
} from 'discord.js';

export function createBannerEmbed(bannerData, user) {
  const embed = new EmbedBuilder()
    .setTitle(bannerData.title.length > 250 ? `${bannerData.title.substring(0, 247)}...` : bannerData.title)
    .setURL(bannerData.pageUrl || 'https://pixabay.com')
    .setImage(bannerData.url)
    .setColor(0x1db954)
    .setFooter({
      text: `🖼️ Banner (${bannerData.dimensions}) • ${bannerData.ratio}:1 • Requested by ${user.username}`,
      iconURL: user.displayAvatarURL()
    })
    .setTimestamp();

  if (bannerData.source === 'surprise') {
    embed.setDescription('🎲 **بانر ديسكورد عريض عشوائي**');
  } else if (bannerData.source === 'fallback') {
    embed.setDescription(`🎨 **بانر جمالي عريض بديل لـ:** \`${bannerData.displayTerm}\``);
  } else {
    embed.setDescription(`🖼️ **بانر ديسكورد عريض لـ:** **${bannerData.displayTerm}**`);
  }

  return embed;
}

export function parseBannerCustomId(customId) {
  const parts = customId.split('|');
  return { action: parts[0] || '', userId: parts[1] || '', term: parts.slice(2).join('|') || '' };
}

export function buildBannerCustomId(action, term, userId) {
  return `${action}|${userId}|${(term || '').replace(/\|/g, '').substring(0, 45)}`;
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
