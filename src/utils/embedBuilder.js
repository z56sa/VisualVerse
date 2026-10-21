import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';

export const embedUtils = {
  colors: {
    primary: 0x5865F2,
    success: 0x57F287,
    warning: 0xFEE75C,
    error: 0xED4245,
    purple: 0x9B59B6,
    dark: 0x2B2D31
  },

  /**
   * Build embed and action buttons for a matching pair
   * Displays banner at the bottom (.setImage) and avatar as thumbnail (.setThumbnail)
   */
  createMatchingPairEmbed(pair, interactionUser) {
    const avatarUrl = pair.avatarUrl || pair.avatar_url || null;
    const bannerUrl = pair.bannerUrl || pair.banner_url || null;
    const pairId = pair.id || 'N/A';
    const pairTitle = pair.title || 'ثنائي متطابق';
    const pairCategory = (pair.category || 'عام').toUpperCase();

    const embed = new EmbedBuilder()
      .setColor(this.colors.purple)
      .setTitle(`✨ ثنائي متطابق: ${pairTitle}`)
      .setDescription(
        `📁 **الفئة:** \`${pairCategory}\`\n` +
        `🆔 **المعرف:** \`#${pairId}\`\n\n` +
        `> 💡 *الصورة بالأسفل هي **البنر (Banner)**، بينما المصغرة في الزاوية هي **الافتار (Avatar)**.*`
      )
      .setFooter({
        text: `طلب بواسطة ${interactionUser.username} • VisualVerse Studio`,
        iconURL: interactionUser.displayAvatarURL({ dynamic: true })
      })
      .setTimestamp();

    // Set Avatar in the corner (Thumbnail)
    if (avatarUrl && typeof avatarUrl === 'string' && avatarUrl.trim().length > 0) {
      embed.setThumbnail(avatarUrl.trim());
    }

    // Set Banner at the bottom full size (Image)
    if (bannerUrl && typeof bannerUrl === 'string' && bannerUrl.trim().length > 0) {
      embed.setImage(bannerUrl.trim());
    }

    // Interactive Action Row
    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId(`matching_next_${pair.category || 'all'}_${pairId}`)
        .setLabel('صورة أخرى 🔄')
        .setStyle(ButtonStyle.Primary)
    );

    // Add Avatar download link button if valid URL
    if (avatarUrl && avatarUrl.startsWith('http')) {
      row.addComponents(
        new ButtonBuilder()
          .setLabel('تحميل افتار HD 📥')
          .setStyle(ButtonStyle.Link)
          .setURL(avatarUrl.trim())
      );
    }

    // Add Banner download link button if valid URL
    if (bannerUrl && bannerUrl.startsWith('http')) {
      row.addComponents(
        new ButtonBuilder()
          .setLabel('تحميل بنر HD 📥')
          .setStyle(ButtonStyle.Link)
          .setURL(bannerUrl.trim())
      );
    }

    // Send to DM button
    row.addComponents(
      new ButtonBuilder()
        .setCustomId(`matching_dm_${pairId}`)
        .setLabel('إرسال للخاص 📩')
        .setStyle(ButtonStyle.Secondary)
    );

    return { embed, row };
  },

  /**
   * Build embed for User Media (/get-media)
   */
  createUserMediaEmbed(targetUser, fetchedUser) {
    const avatarUrl = targetUser.displayAvatarURL({ size: 1024, extension: 'png', forceStatic: false });
    const bannerUrl = fetchedUser.bannerURL({ size: 1024, extension: 'png', forceStatic: false });
    const bannerColor = fetchedUser.hexAccentColor || '#2B2D31';

    const embed = new EmbedBuilder()
      .setColor(fetchedUser.accentColor || this.colors.primary)
      .setTitle(`🎨 وسائط البروفايل: ${targetUser.tag}`)
      .setDescription(
        `👤 **اسم المستخدم:** ${targetUser.username}\n` +
        `🆔 **المعرف (ID):** \`${targetUser.id}\`\n` +
        `🎨 **لون الهيدر:** \`${bannerColor}\`\n` +
        `🖼️ **البنر:** ${bannerUrl ? '[اضغط للعرض المباشر](' + bannerUrl + ')' : '❌ لا يوجد بنر مخصص'}`
      )
      .setTimestamp();

    if (avatarUrl) {
      embed.setThumbnail(avatarUrl);
    }

    if (bannerUrl) {
      embed.setImage(bannerUrl);
    }

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setLabel('الافتار بجودة HD 📥')
        .setStyle(ButtonStyle.Link)
        .setURL(avatarUrl)
    );

    if (bannerUrl) {
      row.addComponents(
        new ButtonBuilder()
          .setLabel('البنر بجودة HD 📥')
          .setStyle(ButtonStyle.Link)
          .setURL(bannerUrl)
      );
    }

    return { embed, row };
  },

  success(title, message) {
    return new EmbedBuilder()
      .setColor(this.colors.success)
      .setTitle(`✅ ${title}`)
      .setDescription(message)
      .setTimestamp();
  },

  error(title, message) {
    return new EmbedBuilder()
      .setColor(this.colors.error)
      .setTitle(`❌ ${title}`)
      .setDescription(message)
      .setTimestamp();
  }
};

export default embedUtils;
