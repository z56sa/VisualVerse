import { EmbedBuilder } from 'discord.js';
import { getSmartGif, getTrendingGif } from '../services/giphyService.js';
import { createGifEmbed, createGifActionRow, parseCustomId } from '../utils/gifEmbed.js';

/**
 * Handles incoming button clicks on GIF messages
 * @param {import('discord.js').ButtonInteraction} interaction 
 * @param {string} apiKey 
 */
export async function handleButtonInteraction(interaction, apiKey) {
  const { action, term } = parseCustomId(interaction.customId);

  // 1. "📌 Save" button: DMs the GIF to the user
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
        .setColor(0x5865f2) // Blurple
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

  // 2. "🔄 Another One": Fetches another fresh GIF for the same search term
  if (action === 'another') {
    await interaction.deferUpdate(); // Acknowledges interaction and keeps original message alive while fetching

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

  // 3. "🎲 Surprise Me": Fetches a completely random trending GIF
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
