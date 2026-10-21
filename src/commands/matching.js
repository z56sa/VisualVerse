import { SlashCommandBuilder } from 'discord.js';
import dbService from '../services/database.js';
import embedUtils from '../utils/embedBuilder.js';

export const matchingCommand = {
  data: new SlashCommandBuilder()
    .setName('matching')
    .setDescription('جلب ثنائيات صور وافتارات وبنرات متناسقة بجودة عالية')
    .addStringOption(option =>
      option.setName('category')
        .setDescription('اختر فئة الصور المتطابقة')
        .setRequired(false)
        .addChoices(
          { name: '🌐 الكل (عشوائي)', value: 'all' },
          { name: '🎌 أنمي (Anime)', value: 'anime' },
          { name: '👩‍❤️‍👨 ثنائيات كبلز (Couples)', value: 'couples' },
          { name: '✨ جمالي وفخم (Aesthetic)', value: 'aesthetic' },
          { name: '🎮 ألعاب وجيمينج (Gaming)', value: 'gaming' }
        )
    ),

  async execute(interaction) {
    await interaction.deferReply();

    const category = interaction.options.getString('category') || 'all';
    const pair = dbService.getRandomPair(category);

    if (!pair) {
      return interaction.editReply({
        embeds: [
          embedUtils.error(
            'لا توجد صور متوفرة',
            `لم يتم العثور على أي ثنائيات في فئة \`${category}\`. يمكنك إضافة ثنائيات عبر أمر \`/admin-pair add\`.`
          )
        ]
      });
    }

    const { embed, row } = embedUtils.createMatchingPairEmbed(pair, interaction.user);

    await interaction.editReply({
      embeds: [embed],
      components: [row]
    });
  }
};

export default matchingCommand;
