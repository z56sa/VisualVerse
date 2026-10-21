import http from 'http';
import { Client, GatewayIntentBits, Collection, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } from 'discord.js';
import dotenv from 'dotenv';
import { getSmartBanner, getSurpriseBanner } from './services/pinterestService.js';
import { SlashCommandBuilder, REST, Routes } from 'discord.js';

dotenv.config();

// ─── Health Check Server for Render ──────────────────────────────────────────
const PORT = process.env.PORT || 3000;
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ status: 'ok', bot: client.user?.tag || 'connecting' }));
});
server.listen(PORT, () => console.log(`🌐 Health check server on port ${PORT}`));

// ─── Discord Client ───────────────────────────────────────────────────────────
const { DISCORD_TOKEN, CLIENT_ID, GUILD_ID } = process.env;

if (!DISCORD_TOKEN || !CLIENT_ID) {
  console.error('❌ Missing DISCORD_TOKEN or CLIENT_ID in environment!');
  process.exit(1);
}

// ─── Embed & Button Helpers ───────────────────────────────────────────────────

function createBannerEmbed(bannerData, user) {
  const embed = new EmbedBuilder()
    .setTitle(bannerData.title.length > 250 ? bannerData.title.substring(0, 247) + '...' : bannerData.title)
    .setURL(bannerData.pageUrl || 'https://www.pinterest.com')
    .setImage(bannerData.url)
    .setColor(0xe60023) // Pinterest Red
    .setFooter({
      text: `📌 Pinterest Banner (${bannerData.dimensions}) • Ratio ${bannerData.ratio}:1 • By ${user.username}`,
      iconURL: user.displayAvatarURL()
    })
    .setTimestamp();

  const descriptions = {
    surprise: '🎲 **بانر ديسكورد عريض عشوائي من Pinterest**',
    fallback: `🎨 **بانر بديل عريض لـ:** \`${bannerData.displayTerm}\``,
    default: `🖼️ **بانر ديسكورد عريض لـ:** **${bannerData.displayTerm}**`
  };
  embed.setDescription(descriptions[bannerData.source] || descriptions.default);
  return embed;
}

function buildCustomId(action, term, userId) {
  return `${action}|${userId}|${(term || '').replace(/\|/g, '').substring(0, 45)}`;
}

function parseCustomId(customId) {
  const p = customId.split('|');
  return { action: p[0] || '', userId: p[1] || '', term: p.slice(2).join('|') || '' };
}

function createBannerRow(term, userId) {
  return new ActionRowBuilder().addComponents(
    new ButtonBuilder()
      .setCustomId(buildCustomId('banner_another', term, userId))
      .setLabel('🔄 Another Banner')
      .setStyle(ButtonStyle.Primary),
    new ButtonBuilder()
      .setCustomId(buildCustomId('banner_surprise', term, userId))
      .setLabel('🎲 Surprise Banner')
      .setStyle(ButtonStyle.Secondary),
    new ButtonBuilder()
      .setCustomId(buildCustomId('banner_save', term, userId))
      .setLabel('📌 Save to DM')
      .setStyle(ButtonStyle.Success)
  );
}

// ─── Register Slash Commands ──────────────────────────────────────────────────

async function registerCommands() {
  const bannerCommand = new SlashCommandBuilder()
    .setName('banner')
    .setDescription('جلب بانر ديسكورد عريض مباشرة من Pinterest')
    .addStringOption(opt =>
      opt.setName('search_term')
        .setDescription('أدخل موضوع البانر (anime, cyberpunk, lofi, aesthetic...)')
        .setRequired(true)
        .setMaxLength(100)
    )
    .toJSON();

  const rest = new REST({ version: '10' }).setToken(DISCORD_TOKEN);
  try {
    if (GUILD_ID && GUILD_ID.trim().length > 0) {
      await rest.put(Routes.applicationGuildCommands(CLIENT_ID, GUILD_ID.trim()), { body: [bannerCommand] });
      console.log(`✅ Slash command registered to Guild: ${GUILD_ID}`);
    } else {
      await rest.put(Routes.applicationCommands(CLIENT_ID), { body: [bannerCommand] });
      console.log('✅ Slash command registered globally.');
    }
  } catch (e) {
    console.error('❌ Failed to register commands:', e.message);
  }
}

// ─── Discord Client Setup ────────────────────────────────────────────────────

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.DirectMessages]
});

client.once('clientReady', async readyClient => {
  console.log(`🤖 Logged in as ${readyClient.user.tag}!`);
  console.log('🌟 Pinterest Banner Bot ready.');
  readyClient.user.setActivity('/banner [search_term]', { type: 2 });
  await registerCommands();
});

client.on('interactionCreate', async interaction => {
  try {
    // ─── Slash Command /banner ─────────────────────────────────────────────
    if (interaction.isChatInputCommand() && interaction.commandName === 'banner') {
      const searchTerm = interaction.options.getString('search_term', true);
      await interaction.deferReply();

      const bannerData = await getSmartBanner(searchTerm);
      await interaction.editReply({
        embeds: [createBannerEmbed(bannerData, interaction.user)],
        components: [createBannerRow(searchTerm, interaction.user.id)]
      });
      return;
    }

    // ─── Button Interactions ───────────────────────────────────────────────
    if (interaction.isButton()) {
      const { action, term } = parseCustomId(interaction.customId);

      // 📌 Save to DM
      if (action === 'banner_save') {
        await interaction.deferReply({ flags: 64 });
        try {
          const embed = interaction.message.embeds?.[0];
          if (!embed?.image?.url) {
            await interaction.editReply({ content: '⚠️ لم يتم العثور على صورة لحفظها.' });
            return;
          }
          const dmEmbed = new EmbedBuilder()
            .setTitle(`📌 ${embed.title || 'Pinterest Banner'}`)
            .setURL(embed.url || 'https://www.pinterest.com')
            .setImage(embed.image.url)
            .setColor(0xe60023)
            .setDescription(`محفوظ من **${interaction.guild?.name || 'Discord'}** في <#${interaction.channelId}>`)
            .setFooter({ text: 'Pinterest Banner Bot' })
            .setTimestamp();
          await interaction.user.send({ embeds: [dmEmbed] });
          await interaction.editReply({ content: '✅ تم إرسال البانر إلى رسائلك الخاصة!' });
        } catch {
          await interaction.editReply({ content: '❌ تعذر الإرسال! تأكد من السماح بالرسائل الخاصة.' });
        }
        return;
      }

      // 🔄 Another Banner
      if (action === 'banner_another') {
        await interaction.deferUpdate();
        const data = await getSmartBanner(term || 'anime');
        await interaction.editReply({
          embeds: [createBannerEmbed(data, interaction.user)],
          components: [createBannerRow(term || 'anime', interaction.user.id)]
        });
        return;
      }

      // 🎲 Surprise Banner
      if (action === 'banner_surprise') {
        await interaction.deferUpdate();
        const data = await getSurpriseBanner();
        await interaction.editReply({
          embeds: [createBannerEmbed(data, interaction.user)],
          components: [createBannerRow('surprise', interaction.user.id)]
        });
        return;
      }
    }
  } catch (error) {
    console.error('Interaction error:', error);
    const msg = { content: '❌ حدث خطأ، يرجى المحاولة مرة أخرى!', flags: 64 };
    if (interaction.deferred || interaction.replied) {
      await interaction.followUp(msg).catch(() => {});
    } else {
      await interaction.reply(msg).catch(() => {});
    }
  }
});

process.on('SIGINT', () => { client.destroy(); process.exit(0); });
process.on('SIGTERM', () => { client.destroy(); process.exit(0); });

client.login(DISCORD_TOKEN).catch(err => {
  console.error('❌ Discord login failed:', err.message);
  process.exit(1);
});
