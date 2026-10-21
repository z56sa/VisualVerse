import { SlashCommandBuilder, AttachmentBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';
import videoDownloaderService from '../services/videoDownloader.js';
import embedUtils from '../utils/embedBuilder.js';

export const downloadVideoCommand = {
  data: new SlashCommandBuilder()
    .setName('download-video')
    .setDescription('جلب وتنزيل مقاطع الفيديو من تيك توك، ريلز، يوتيوب، أو تويتر')
    .addStringOption(option =>
      option.setName('url')
        .setDescription('رابط الفيديو المراد تحميله (TikTok / Instagram / YouTube / X)')
        .setRequired(true)
    ),

  async execute(interaction) {
    await interaction.deferReply();

    const videoUrl = interaction.options.getString('url');

    try {
      // Step 1: Resolve downloadable link & metadata
      const mediaInfo = await videoDownloaderService.resolveMedia(videoUrl);

      if (!mediaInfo || !mediaInfo.downloadUrl) {
        return interaction.editReply({
          embeds: [
            embedUtils.error(
              'فشل معالجة الرابط',
              'لم نتمكن من استخراج رابط التنزيل المباشر للمقطع. يرجى التأكد من أن الحساب والفيديو عام وليس خاصاً.'
            )
          ]
        });
      }

      // Step 2: Attempt to download buffer to send natively in chat
      try {
        const { buffer, sizeMB } = await videoDownloaderService.downloadBuffer(mediaInfo.downloadUrl, 24);

        const videoAttachment = new AttachmentBuilder(buffer, { name: `VisualVerse_${Date.now()}.mp4` });

        const embed = new EmbedBuilder()
          .setColor(embedUtils.colors.success)
          .setTitle(`🎬 تم تنزيل المقطع بنجاح (${mediaInfo.platform || 'فيديو'})`)
          .setDescription(
            `📌 **العنوان:** ${mediaInfo.title || 'بدون عنوان'}\n` +
            `👤 **الناشر:** ${mediaInfo.author || 'غير معروف'}\n` +
            `📦 **الحجم:** \`${sizeMB} MB\``
          )
          .setFooter({
            text: `طلب بواسطة ${interaction.user.username} • VisualVerse Studio`,
            iconURL: interaction.user.displayAvatarURL({ dynamic: true })
          })
          .setTimestamp();

        const row = new ActionRowBuilder().addComponents(
          new ButtonBuilder()
            .setLabel('رابط التحميل المباشر 🔗')
            .setStyle(ButtonStyle.Link)
            .setURL(mediaInfo.downloadUrl)
        );

        return await interaction.editReply({
          embeds: [embed],
          files: [videoAttachment],
          components: [row]
        });
      } catch (streamErr) {
        // Fallback: If video buffer exceeds Discord's upload limit (e.g. > 25MB) or stream fails, send link & preview
        const embed = new EmbedBuilder()
          .setColor(embedUtils.colors.warning)
          .setTitle(`🎬 تم استخراج رابط المقطع (${mediaInfo.platform || 'فيديو'})`)
          .setDescription(
            `📌 **العنوان:** ${mediaInfo.title || 'بدون عنوان'}\n` +
            `👤 **الناشر:** ${mediaInfo.author || 'غير معروف'}\n\n` +
            `⚠️ *حجم المقطع يتجاوز حد إرسال الملفات المباشر على ديسكورد، يمكنك تنزيله مباشرة أو مشاهدته عبر الزر أدناه.*`
          )
          .setFooter({
            text: `طلب بواسطة ${interaction.user.username}`,
            iconURL: interaction.user.displayAvatarURL({ dynamic: true })
          })
          .setTimestamp();

        if (mediaInfo.thumbnail) {
          embed.setThumbnail(mediaInfo.thumbnail);
        }

        const row = new ActionRowBuilder().addComponents(
          new ButtonBuilder()
            .setLabel('تنزيل المقطع مباشرة HD 📥')
            .setStyle(ButtonStyle.Link)
            .setURL(mediaInfo.downloadUrl)
        );

        return await interaction.editReply({
          embeds: [embed],
          components: [row]
        });
      }
    } catch (err) {
      console.error('Error downloading video:', err);
      return await interaction.editReply({
        embeds: [
          embedUtils.error(
            'حدث خطأ أثناء تنزيل الفيديو',
            `السبب: ${err.message || 'تعذر الاتصال بخوادم التنزيل'}`
          )
        ]
      });
    }
  }
};

export default downloadVideoCommand;
