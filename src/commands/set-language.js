import { SlashCommandBuilder, PermissionFlagsBits, EmbedBuilder } from 'discord.js';
import { loadFeedsConfig, saveFeedsConfig } from '../services/storageService.js';

export const setLanguageCommand = {
  data: new SlashCommandBuilder()
    .setName('set-language')
    .setDescription('Set default bot language for this server | ضبط لغة البوت الافتراضية للسيرفر')
    .setDefaultMemberPermissions(PermissionFlagsBits.ManageGuild)
    .addStringOption(option =>
      option
        .setName('language')
        .setDescription('Choose language | اختر اللغة')
        .setRequired(true)
        .addChoices(
          { name: '🇸🇦 العربية (Arabic)', value: 'ar' },
          { name: '🇺🇸 English (الإنجليزية)', value: 'en' }
        )
    ),

  async execute(interaction) {
    await interaction.deferReply({ ephemeral: true });

    const language = interaction.options.getString('language', true);
    const guildId = interaction.guildId;
    const isArabic = language === 'ar';

    const config = loadFeedsConfig();
    if (!config[guildId]) {
      config[guildId] = {
        channelId: null,
        language,
        feeds: [],
        lastPostedUrls: []
      };
    } else {
      config[guildId].language = language;
    }

    saveFeedsConfig(config);

    const embed = new EmbedBuilder()
      .setColor(0x5865F2)
      .setTitle(isArabic ? '🌐 تم ضبط لغة السيرفر بنجاح!' : '🌐 Server Language Updated Successfully!')
      .setDescription(
        isArabic
          ? 'تم اعتماد **اللغة العربية 🇸🇦** كلغة افتراضية للبوت وتلخيص الأخبار في هذا السيرفر.\nجميع الأوامر والنشرات التلقائية ستصدر بالعربية.'
          : 'Default language has been set to **English 🇺🇸** for this server.\nAll automated feeds and commands will default to English.'
      )
      .setFooter({ text: 'FeedPulse • Language Settings' })
      .setTimestamp();

    await interaction.editReply({ embeds: [embed] });
  }
};
