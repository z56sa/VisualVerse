import { SlashCommandBuilder } from 'discord.js';
import { fetchFeedItems, DEFAULT_FEEDS } from '../services/feedService.js';
import { summarizeNewsItem } from '../services/aiService.js';
import { createNewsEmbed, createNewsActionRow } from '../utils/embedBuilder.js';
import { loadFeedsConfig } from '../services/storageService.js';

export const latestNewsCommand = {
  data: new SlashCommandBuilder()
    .setName('latest-news')
    .setDescription('Fetch & summarize the latest 3 news articles with AI | جلب وتلخيص أحدث 3 أخبار')
    .addStringOption(option =>
      option
        .setName('category')
        .setDescription('News category | تصنيف الأخبار')
        .addChoices(
          { name: '🎮 Gaming — ألعاب (IGN)', value: 'gaming' },
          { name: '💻 Tech — تكنولوجيا (The Verge)', value: 'tech' },
          { name: '🌸 Anime — أنمي (ANN)', value: 'anime' }
        )
    ),

  async execute(interaction, geminiApiKey) {
    await interaction.deferReply();

    const category = interaction.options.getString('category');
    const config = loadFeedsConfig();
    const guildConfig = config[interaction.guildId];
    
    // الافتراضي هو العربية دائماً إلا إذا اختار الإنجليزية صراحة
    const lang = (guildConfig?.language === 'en') ? 'en' : 'ar';
    const isArabic = lang === 'ar';

    let targetFeedUrl = null;
    if (category) {
      const found = DEFAULT_FEEDS.find(f => f.category === category);
      if (found) targetFeedUrl = found.url;
    } else {
      const guildFeeds = guildConfig?.feeds;
      if (guildFeeds && guildFeeds.length > 0) {
        targetFeedUrl = guildFeeds[0];
      } else {
        targetFeedUrl = DEFAULT_FEEDS[0].url;
      }
    }

    try {
      const feedData = await fetchFeedItems(targetFeedUrl, 3);

      if (!feedData.items || feedData.items.length === 0) {
        await interaction.editReply({
          content: isArabic
            ? '⚠️ لم يتم العثور على أي أخبار حالياً في هذا المصدر.'
            : '⚠️ No news items found in this feed right now.'
        });
        return;
      }

      await interaction.editReply({
        content: isArabic
          ? `🤖 **جاري تحليل وتلخيص الأخبار من: ${feedData.feedTitle}...**`
          : `🤖 **Analyzing and summarizing news from: ${feedData.feedTitle}...**`
      });

      for (let i = 0; i < feedData.items.length; i++) {
        const item = feedData.items[i];

        const aiResult = await summarizeNewsItem(
          geminiApiKey,
          item.title,
          item.contentSnippet,
          lang
        );

        const embed = createNewsEmbed({
          title: aiResult.formattedTitle,
          summaryPoints: aiResult.summaryPoints,
          link: item.link,
          imageUrl: item.imageUrl,
          pubDate: item.pubDate,
          sourceName: feedData.feedTitle,
          lang
        });

        const row = createNewsActionRow(item.link, lang);

        if (i === 0) {
          await interaction.editReply({ content: null, embeds: [embed], components: [row] });
        } else {
          await interaction.followUp({ embeds: [embed], components: [row] });
        }
      }

    } catch (err) {
      console.error('[LatestNews] Error:', err);
      await interaction.editReply({
        content: isArabic
          ? `❌ تعذر جلب الأخبار: \`${err.message}\``
          : `❌ Could not fetch news: \`${err.message}\``
      });
    }
  }
};
