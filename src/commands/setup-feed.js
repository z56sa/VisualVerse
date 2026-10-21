import { SlashCommandBuilder, PermissionFlagsBits, ChannelType } from 'discord.js';
import { loadFeedsConfig, saveFeedsConfig } from '../services/storageService.js';
import { fetchFeedItems } from '../services/feedService.js';

export const setupFeedCommand = {
  data: new SlashCommandBuilder()
    .setName('setup-feed')
    .setDescription('ربط مصدر أخبار RSS بقناة معينة وتحديد لغة التلخيص (عربي / إنجليزي)')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addChannelOption(option =>
      option
        .setName('channel')
        .setDescription('الروم المراد إرسال الأخبار الملخصة إليها')
        .addChannelTypes(ChannelType.GuildText, ChannelType.GuildAnnouncement)
        .setRequired(true)
    )
    .addStringOption(option =>
      option
        .setName('url')
        .setDescription('رابط خلاصة الـ RSS لموقع الأخبار (ألعاب، أنمي، تكنولوجيا...)')
        .setRequired(true)
    )
    .addStringOption(option =>
      option
        .setName('language')
        .setDescription('لغة تلخيص الأخبار (العربية أو الإنجليزية)')
        .addChoices(
          { name: '🇸🇦 العربية (Arabic)', value: 'ar' },
          { name: '🇺🇸 English (الإنجليزية)', value: 'en' }
        )
    ),

  async execute(interaction) {
    await interaction.deferReply({ ephemeral: true });

    const channel = interaction.options.getChannel('channel', true);
    const feedUrl = interaction.options.getString('url', true).trim();
    const language = interaction.options.getString('language') || 'ar';
    const guildId = interaction.guildId;

    try {
      const feedData = await fetchFeedItems(feedUrl, 1);

      const config = loadFeedsConfig();
      if (!config[guildId]) {
        config[guildId] = {
          channelId: channel.id,
          language,
          feeds: [],
          lastPostedUrls: []
        };
      }

      config[guildId].channelId = channel.id;
      config[guildId].language = language;
      if (!config[guildId].feeds.includes(feedUrl)) {
        config[guildId].feeds.push(feedUrl);
      }

      saveFeedsConfig(config);

      const langText = language === 'ar' ? 'العربية 🇸🇦' : 'English 🇺🇸';

      await interaction.editReply({
        content: `✅ **تم إعداد FeedPulse بنجاح!**\n\n📌 **الروم:** <#${channel.id}>\n🌐 **المصدر:** ${feedData.feedTitle}\n🗣️ **اللغة:** ${langText}\n🔗 **الرابط:** \`${feedUrl}\`\n\nسيبدأ البوت بفحص المصدر تلقائياً وتلخيص الأخبار الجديدة فور صدورها! ⚡`
      });
    } catch (err) {
      await interaction.editReply({
        content: `❌ **فشل التحقق من الرابط!**\nتأكد أن الرابط هو خلاصة RSS صالحة.\nتفاصيل الخطأ: \`${err.message}\``
      });
    }
  }
};
