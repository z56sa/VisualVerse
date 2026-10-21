import { SlashCommandBuilder } from 'discord.js';
import { fetchFeedItems, DEFAULT_FEEDS } from '../services/feedService.js';
import { summarizeNewsItem } from '../services/aiService.js';
import { createNewsEmbed, createNewsActionRow } from '../utils/embedBuilder.js';
import { loadFeedsConfig } from '../services/storageService.js';

export const latestNewsCommand = {
  data: new SlashCommandBuilder()
    .setName('latest-news')
    .setDescription('جلب وتلخيص أحدث 3 أخبار فوراً في الشات بواسطة الذكاء الاصطناعي')
    .addStringOption(option =>
      option
        .setName('category')
        .setDescription('اختر تصنيف الأخبار (أو سيتم استخدام خلاصات سيرفرك)')
        .addChoices(
          { name: '🎮 ألعاب (IGN)', value: 'gaming' },
          { name: '💻 تكنولوجيا (The Verge)', value: 'tech' },
          { name: '🌸 أنمي (Anime News Network)', value: 'anime' }
        )
    ),

  async execute(interaction, geminiApiKey) {
    await interaction.deferReply();

    const category = interaction.options.getString('category');
    let targetFeedUrl = null;

    if (category) {
      const found = DEFAULT_FEEDS.find(f => f.category === category);
      if (found) targetFeedUrl = found.url;
    } else {
      // استخدام أول خلاصة مسجلة للسيرفر إن وجدت
      const config = loadFeedsConfig();
      const guildFeeds = config[interaction.guildId]?.feeds;
      if (guildFeeds && guildFeeds.length > 0) {
        targetFeedUrl = guildFeeds[0];
      } else {
        targetFeedUrl = DEFAULT_FEEDS[0].url; // الافتراضي: ألعاب
      }
    }

    try {
      const feedData = await fetchFeedItems(targetFeedUrl, 3);
      if (!feedData.items || feedData.items.length === 0) {
        await interaction.editReply({ content: '⚠️ لم يتم العثور على أي أخبار حالياً في المصدر.' });
        return;
      }

      await interaction.editReply({
        content: `⚡ **جاري معالجة وتلخيص أحدث الأخبار من: ${feedData.feedTitle}...**`
      });

      for (let i = 0; i < feedData.items.length; i++) {
        const item = feedData.items[i];
        const aiResult = await summarizeNewsItem(geminiApiKey, item.title, item.contentSnippet);

        const embed = createNewsEmbed({
          arabicTitle: aiResult.arabicTitle,
          originalTitle: item.title,
          summaryPoints: aiResult.summaryPoints,
          link: item.link,
          imageUrl: item.imageUrl,
          pubDate: item.pubDate,
          sourceName: feedData.feedTitle
        });

        const row = createNewsActionRow(item.link);

        if (i === 0) {
          await interaction.editReply({ content: null, embeds: [embed], components: [row] });
        } else {
          await interaction.followUp({ embeds: [embed], components: [row] });
        }
      }
    } catch (err) {
      await interaction.editReply({
        content: `❌ تعذر جلب الأخبار: \`${err.message}\``
      });
    }
  }
};
