import { SlashCommandBuilder, EmbedBuilder } from 'discord.js';
import { fetchFeedItems, DEFAULT_FEEDS } from '../services/feedService.js';
import { generateDailyRecapWithLang } from '../services/aiService.js';
import { loadFeedsConfig } from '../services/storageService.js';

export const dailyRecapCommand = {
  data: new SlashCommandBuilder()
    .setName('daily-recap')
    .setDescription('توليد ملخص شامل وحصاد يومي لأهم الأخبار (بالعربية أو الإنجليزية)')
    .addStringOption(option =>
      option
        .setName('language')
        .setDescription('اختر لغة الحصاد الإخباري')
        .addChoices(
          { name: '🇸🇦 العربية (Arabic)', value: 'ar' },
          { name: '🇺🇸 English (الإنجليزية)', value: 'en' }
        )
    ),

  async execute(interaction, geminiApiKey) {
    await interaction.deferReply();

    const selectedLang = interaction.options.getString('language');
    const config = loadFeedsConfig();
    const guildConfig = config[interaction.guildId];
    const lang = selectedLang || guildConfig?.language || 'ar';
    const isArabic = lang === 'ar';

    const feedsToScan = (guildConfig && guildConfig.feeds?.length > 0)
      ? guildConfig.feeds
      : DEFAULT_FEEDS.map(f => f.url);

    try {
      const allNews = [];

      for (const url of feedsToScan.slice(0, 3)) {
        try {
          const feed = await fetchFeedItems(url, 2);
          for (const item of feed.items) {
            allNews.push({ title: item.title, source: feed.feedTitle });
          }
        } catch {}
      }

      if (allNews.length === 0) {
        await interaction.editReply({
          content: isArabic ? '⚠️ لا توجد أخبار كافية لتوليد حصاد اليوم.' : '⚠️ Not enough news items to generate a daily recap.'
        });
        return;
      }

      const recapText = await generateDailyRecapWithLang(geminiApiKey, allNews, lang);

      const recapEmbed = new EmbedBuilder()
        .setColor(0x5865F2)
        .setTitle(isArabic ? '⚡ حصاد اليوم الإخباري من FeedPulse' : '⚡ FeedPulse Daily News Highlights')
        .setDescription(recapText)
        .setFooter({ text: isArabic ? 'FeedPulse • تلخيص يومي ذكي' : 'FeedPulse • Smart Daily Recap' })
        .setTimestamp();

      await interaction.editReply({ embeds: [recapEmbed] });
    } catch (err) {
      await interaction.editReply({
        content: `❌ Error: \`${err.message}\``
      });
    }
  }
};
