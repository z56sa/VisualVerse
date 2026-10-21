import { EmbedBuilder } from 'discord.js';
import { getSmartGif, getTrendingGif } from '../services/giphyService.js';
import { createGifEmbed, createGifActionRow, parseCustomId } from '../utils/gifEmbed.js';
import { getSmartBanner, getSurpriseBanner } from '../services/bannerService.js';
import { createBannerEmbed, createBannerActionRow, parseBannerCustomId } from '../utils/bannerEmbed.js';

/**
 * Handles incoming button clicks on GIF & Banner messages
 * @param {import('discord.js').ButtonInteraction} interaction 
 * @param {string} apiKey 
 */
export async function handleButtonInteraction(interaction, apiKey) {
  const customId = interaction.customId;

  // --- BANNER BUTTONS ---
  if (customId.startsWith('banner_')) {
    const { action, term } = parseBannerCustomId(customId);

    // 1. "📌 Save" Banner
    if (action === 'banner_save') {
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
          .setFooter({ text: 'Saved via Animated Banner Bot' })
          .setTimestamp();

        await interaction.user.send({ embeds: [dmEmbed] });

        await interaction.editReply({
          content: '✅ This Animated Banner has been sent directly to your DMs!'
        });
      } catch (err) {
        console.warn(`Failed to DM user ${interaction.user.tag}:`, err.message);
        await interaction.editReply({
          content: '❌ Could not send you a DM! Please make sure your server privacy settings allow Direct Messages from server members.'
        });
      }
      return;
    }

    // 2. "🔄 Another Banner"
    if (action === 'banner_another') {
      await interaction.deferUpdate();

      const targetTerm = term || 'aesthetic banner';
      const bannerData = await getSmartBanner(apiKey, targetTerm);
      const newEmbed = createBannerEmbed(bannerData, interaction.user);
      const newRow = createBannerActionRow(targetTerm, interaction.user.id);

      await interaction.editReply({
        embeds: [newEmbed],
        components: [newRow]
      });
      return;
    }

    // 3. "🎲 Surprise Banner"
    if (action === 'banner_surprise') {
      await interaction.deferUpdate();

      const bannerData = await getSurpriseBanner(apiKey);
      const newEmbed = createBannerEmbed(bannerData, interaction.user);
      const newRow = createBannerActionRow('surprise banner', interaction.user.id);

      await interaction.editReply({
        embeds: [newEmbed],
        components: [newRow]
      });
      return;
    }
    return;
  }

  // --- GIF BUTTONS ---
  const { action, term } = parseCustomId(customId);

  // 1. "📌 Save" GIF
  if (action === 'save') {
    await interaction.deferReply({ ephemeral: true });

    try {
      const messageEmbed = interaction.message.embeds?.[0];
      const gifUrl = messageEmbed?.image?.url;
      const gifTitle = messageEmbed?.title || 'Saved GIF';

      if (!gifUrl) {
        await interaction.editReply({
          content: '⚠️ Could not find a GIF image in this message to save.'
        });
        return;
      }

      const dmEmbed = new EmbedBuilder()
        .setTitle(`📌 Saved: ${gifTitle}`)
        .setURL(messageEmbed.url || gifUrl)
        .setImage(gifUrl)
        .setColor(0x5865f2)
        .setDescription(`Saved from **${interaction.guild?.name || 'Discord'}** in <#${interaction.channelId}>`)
        .setFooter({ text: 'Saved via Giphy Bot' })
        .setTimestamp();

      await interaction.user.send({ embeds: [dmEmbed] });

      await interaction.editReply({
        content: '✅ This GIF has been sent to your Direct Messages (DMs)!'
      });
    } catch (err) {
      console.warn(`Failed to DM user ${interaction.user.tag}:`, err.message);
      await interaction.editReply({
        content: '❌ Could not send you a DM! Please make sure your server privacy settings allow Direct Messages from server members.'
      });
    }
    return;
  }

  // 2. "🔄 Another One" GIF
  if (action === 'another') {
    await interaction.deferUpdate();

    const targetTerm = term || 'random';
    const gifData = await getSmartGif(apiKey, targetTerm);
    const newEmbed = createGifEmbed(gifData, interaction.user);
    const newRow = createGifActionRow(targetTerm, interaction.user.id);

    await interaction.editReply({
      embeds: [newEmbed],
      components: [newRow]
    });
    return;
  }

  // 3. "🎲 Surprise Me" GIF
  if (action === 'surprise') {
    await interaction.deferUpdate();

    let gifData = await getTrendingGif(apiKey);
    if (!gifData) {
      gifData = await getSmartGif(apiKey, 'random surprise');
    }

    const newEmbed = createGifEmbed(gifData, interaction.user);
    const newRow = createGifActionRow('trending', interaction.user.id);

    await interaction.editReply({
      embeds: [newEmbed],
      components: [newRow]
    });
    return;
  }
}
