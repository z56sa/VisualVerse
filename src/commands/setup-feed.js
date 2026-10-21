import { SlashCommandBuilder, PermissionFlagsBits, ChannelType } from 'discord.js';
import { loadFeedsConfig, saveFeedsConfig } from '../services/storageService.js';
import { fetchFeedItems } from '../services/feedService.js';

export const setupFeedCommand = {
  data: new SlashCommandBuilder()
    .setName('setup-feed')
    .setDescription('ربط مصدر أخبار RSS بقناة معينة ليتم النشر التلقائي فيها')
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
    ),

  async execute(interaction) {
    await interaction.deferReply({ ephemeral: true });

    const channel = interaction.options.getChannel('channel', true);
    const feedUrl = interaction.options.getString('url', true).trim();
    const guildId = interaction.guildId;

    try {
      // التحقق من صحة رابط الـ RSS
      const feedData = await fetchFeedItems(feedUrl, 1);

      const config = loadFeedsConfig();
      if (!config[guildId]) {
        config[guildId] = {
          channelId: channel.id,
          feeds: [],
          lastPostedUrls: []
        };
      }

      config[guildId].channelId = channel.id;
      if (!config[guildId].feeds.includes(feedUrl)) {
        config[guildId].feeds.push(feedUrl);
      }

      saveFeedsConfig(config);

      await interaction.editReply({
        content: `✅ **تم إعداد FeedPulse بنجاح!**\n\n📌 **الروم:** <#${channel.id}>\n🌐 **المصدر:** ${feedData.feedTitle}\n🔗 **الرابط:** \`${feedUrl}\`\n\nسيبدأ البوت بفحص المصدر تلقائياً وتلخيص الأخبار الجديدة أولاً بأول! ⚡`
      });
    } catch (err) {
      await interaction.editReply({
        content: `❌ **فشل التحقق من الرابط!**\nتأكد أن الرابط هو خلاصة RSS صالحة (ينتهي عادة بـ \`.xml\` أو \`/feed\` أو \`/rss\`).\nتفاصيل الخطأ: \`${err.message}\``
      });
    }
  }
};
