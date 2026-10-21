import { SlashCommandBuilder, PermissionFlagsBits, ChannelType, EmbedBuilder } from 'discord.js';
import { loadFeedsConfig, saveFeedsConfig } from '../services/storageService.js';
import { fetchFeedItems } from '../services/feedService.js';

export const setupFeedCommand = {
  data: new SlashCommandBuilder()
    .setName('setup-feed')
    .setDescription('Link an RSS feed to a channel | ربط مصدر RSS بقناة')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addChannelOption(option =>
      option
        .setName('channel')
        .setDescription('Channel to post news in | الروم المراد إرسال الأخبار إليه')
        .addChannelTypes(ChannelType.GuildText, ChannelType.GuildAnnouncement)
        .setRequired(true)
    )
    .addStringOption(option =>
      option
        .setName('url')
        .setDescription('RSS feed URL (gaming, anime, tech...) | رابط خلاصة RSS')
        .setRequired(true)
    )
    .addStringOption(option =>
      option
        .setName('language')
        .setDescription('Summary language | لغة التلخيص')
        .addChoices(
          { name: '🇸🇦 العربية (Arabic)', value: 'ar' },
          { name: '🇺🇸 English', value: 'en' }
        )
    ),

  async execute(interaction) {
    await interaction.deferReply({ ephemeral: true });

    const channel = interaction.options.getChannel('channel', true);
    const feedUrl = interaction.options.getString('url', true).trim();
    const language = interaction.options.getString('language') || 'ar';
    const guildId = interaction.guildId;
    const isArabic = language === 'ar';

    try {
      const feedData = await fetchFeedItems(feedUrl, 1);

      const config = loadFeedsConfig();
      if (!config[guildId]) {
        config[guildId] = { channelId: channel.id, language, feeds: [], lastPostedUrls: [] };
      }

      config[guildId].channelId = channel.id;
      config[guildId].language = language;
      if (!config[guildId].feeds.includes(feedUrl)) {
        config[guildId].feeds.push(feedUrl);
      }

      saveFeedsConfig(config);

      const embed = new EmbedBuilder()
        .setColor(0x57F287)
        .setTitle(isArabic ? '✅ تم إعداد FeedPulse بنجاح!' : '✅ FeedPulse Setup Complete!')
        .addFields(
          {
            name: isArabic ? '📌 الروم' : '📌 Channel',
            value: `<#${channel.id}>`,
            inline: true
          },
          {
            name: isArabic ? '🗣️ اللغة' : '🗣️ Language',
            value: isArabic ? 'العربية 🇸🇦' : 'English 🇺🇸',
            inline: true
          },
          {
            name: isArabic ? '🌐 المصدر' : '🌐 Feed Source',
            value: feedData.feedTitle || feedUrl,
            inline: false
          },
          {
            name: isArabic ? '🔗 الرابط' : '🔗 URL',
            value: `\`${feedUrl}\``,
            inline: false
          }
        )
        .setDescription(
          isArabic
            ? '⚡ سيبدأ البوت بمراقبة المصدر تلقائياً وتلخيص الأخبار الجديدة فور صدورها!'
            : '⚡ The bot will now monitor this feed and automatically summarize new articles!'
        )
        .setFooter({ text: 'FeedPulse • Auto News Aggregator' })
        .setTimestamp();

      await interaction.editReply({ embeds: [embed] });

    } catch (err) {
      await interaction.editReply({
        content: isArabic
          ? `❌ **فشل التحقق من الرابط!**\nتأكد أن الرابط خلاصة RSS صالحة.\n\`${err.message}\``
          : `❌ **Invalid RSS feed URL!**\nMake sure the URL is a valid RSS feed.\n\`${err.message}\``
      });
    }
  }
};
