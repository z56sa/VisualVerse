import { SlashCommandBuilder, EmbedBuilder } from 'discord.js';
import { fetchFeedItems, DEFAULT_FEEDS } from '../services/feedService.js';
import { generateDailyRecap } from '../services/aiService.js';
import { loadFeedsConfig } from '../services/storageService.js';

export const dailyRecapCommand = {
  data: new SlashCommandBuilder()
    .setName('daily-recap')
    .setDescription('توليد ملخص شامل وحصاد يومي لأهم الأخبار بضغطة زر باستخدام الذكاء الاصطناعي'),

  async execute(interaction, geminiApiKey) {
    await interaction.deferReply();

    const config = loadFeedsConfig();
    const guildConfig = config[interaction.guildId];
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
        } catch {
          // تجاهل المصادر التي قد تكون غير متاحة مؤقتاً
        }
      }

      if (allNews.length === 0) {
        await interaction.editReply({ content: '⚠️ لا توجد أخبار كافية لتوليد حصاد اليوم.' });
        return;
      }

      const recapText = await generateDailyRecap(geminiApiKey, allNews);

      const recapEmbed = new EmbedBuilder()
        .setColor(0x5865F2)
        .setTitle('⚡ حصاد اليوم الإخباري من FeedPulse')
        .setDescription(recapText)
        .setFooter({ text: 'FeedPulse • تلخيص يومي ذكي' })
        .setTimestamp();

      await interaction.editReply({ embeds: [recapEmbed] });
    } catch (err) {
      await interaction.editReply({
        content: `❌ حدث خطأ أثناء إعداد الملخص: \`${err.message}\``
      });
    }
  }
};
