import { EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';

export const embedUtils = {
  /**
   * Primary brand color (Blurple / Violet gradient aesthetic)
   */
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
   */
  createMatchingPairEmbed(pair, interactionUser) {
    const embed = new EmbedBuilder()
      .setColor(this.colors.purple)
      .setTitle(`✨ ثنائي متطابق: ${pair.title}`)
      .setDescription(
        `📁 **الفئة:** \`${pair.category.toUpperCase()}\`\n` +
        `🆔 **المعرف:** \`#${pair.id}\`\n\n` +
        `> 💡 *الصورة بالأسفل هي **البنر (Banner)**، بينما المصغرة في الزاوية هي **الافتار (Avatar)**.*`
      )
      .setThumbnail(pair.avatar_url)
      .setImage(pair.banner_url)
      .setFooter({
        text: `طلب بواسطة ${interactionUser.username} • VisualVerse Studio`,
        iconURL: interactionUser.displayAvatarURL({ dynamic: true })
      })
      .setTimestamp();

    // Interactive Action Row
    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder()
        .setCustomId(`matching_next_${pair.category}`)
        .setLabel('صورة أخرى 🔄')
        .setStyle(ButtonStyle.Primary),

      new ButtonBuilder()
        .setLabel('تحميل افتار HD 📥')
        .setStyle(ButtonStyle.Link)
        .setURL(pair.avatar_url),

      new ButtonBuilder()
        .setLabel('تحميل بنر HD 📥')
        .setStyle(ButtonStyle.Link)
        .setURL(pair.banner_url),

      new ButtonBuilder()
        .setCustomId(`matching_dm_${pair.id}`)
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
      .setThumbnail(avatarUrl)
      .setTimestamp();

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

  /**
   * Build success message embed
   */
  success(title, message) {
    return new EmbedBuilder()
      .setColor(this.colors.success)
      .setTitle(`✅ ${title}`)
      .setDescription(message)
      .setTimestamp();
  },

  /**
   * Build error message embed
   */
  error(title, message) {
    return new EmbedBuilder()
      .setColor(this.colors.error)
      .setTitle(`❌ ${title}`)
      .setDescription(message)
      .setTimestamp();
  }
};

export default embedUtils;
