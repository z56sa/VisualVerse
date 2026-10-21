import http from 'http';
import {
  Client,
  GatewayIntentBits,
  EmbedBuilder,
  ActionRowBuilder,
  ButtonBuilder,
  ButtonStyle,
  SlashCommandBuilder,
  REST,
  Routes
} from 'discord.js';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ─── Health Check Server for Render ──────────────────────────────────────────
const PORT = process.env.PORT || 3000;
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ status: 'ok', bot: client.user?.tag || 'connecting' }));
});
server.listen(PORT, () => console.log(`🌐 Health check server on port ${PORT}`));

// ─── Load Local Banners Database ─────────────────────────────────────────────
const bannersDbPath = path.join(__dirname, 'banners.json');
let bannersDb = {};

try {
  const data = fs.readFileSync(bannersDbPath, 'utf8');
  bannersDb = JSON.parse(data);
  console.log(`✅ Loaded banners database with categories:`, Object.keys(bannersDb));
} catch (err) {
  console.error('❌ Failed to load banners.json:', err.message);
  bannersDb = {
    anime: [
      {
        title: 'Anime Scenic Horizon',
        url: 'https://media.giphy.com/media/xT9IgzoKnwFNmISR8I/giphy.gif',
        dimensions: '1000x400',
        ratio: '2.50'
      }
    ]
  };
}

// ─── Banner Selection Logic ──────────────────────────────────────────────────
function pickRandom(arr) {
  if (!Array.isArray(arr) || arr.length === 0) return null;
  return arr[Math.floor(Math.random() * arr.length)];
}

function getBannerByCategory(searchTerm) {
  const term = (searchTerm || 'anime').toLowerCase().trim();
  const categories = Object.keys(bannersDb);

  // البحث عن فئة مطابقة
  let matchedCategory = categories.find(cat => term.includes(cat) || cat.includes(term));

  if (!matchedCategory) {
    if (term.includes('game') || term.includes('play')) matchedCategory = 'gaming';
    else if (term.includes('chill') || term.includes('relax')) matchedCategory = 'lofi';
    else if (term.includes('neon') || term.includes('synth')) matchedCategory = 'cyberpunk';
    else if (term.includes('sky') || term.includes('star') || term.includes('space')) matchedCategory = 'nature';
    else matchedCategory = 'anime'; // الافتراضي
  }

  const categoryList = bannersDb[matchedCategory] || bannersDb.anime || [];
  const selected = pickRandom(categoryList);

  return {
    title: selected.title || 'Discord Animated Banner',
    url: selected.url,
    dimensions: selected.dimensions || 'Wide Banner',
    ratio: selected.ratio || '2.00',
    category: matchedCategory,
    displayTerm: searchTerm || matchedCategory
  };
}

function getSurpriseBanner() {
  const categories = Object.keys(bannersDb);
  const randomCat = pickRandom(categories) || 'anime';
  return getBannerByCategory(randomCat);
}

// ─── Embed & Action Row Helpers ───────────────────────────────────────────────
function createBannerEmbed(bannerData, user) {
  return new EmbedBuilder()
    .setTitle(bannerData.title)
    .setImage(bannerData.url)
    .setColor(0x5865f2) // Discord Blurple
    .setDescription(`🖼️ **بانر ديسكورد عريض متحرك لـ:** **${bannerData.displayTerm}**`)
    .setFooter({
      text: `Discord Banner (${bannerData.dimensions}) • Ratio ${bannerData.ratio}:1 • By ${user.username}`,
      iconURL: user.displayAvatarURL()
    })
    .setTimestamp();
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

// ─── Slash Command Registration ───────────────────────────────────────────────
const { DISCORD_TOKEN, CLIENT_ID, GUILD_ID } = process.env;

if (!DISCORD_TOKEN || !CLIENT_ID) {
  console.error('❌ Missing DISCORD_TOKEN or CLIENT_ID in environment variables!');
  process.exit(1);
}

async function registerCommands() {
  const bannerCommand = new SlashCommandBuilder()
    .setName('banner')
    .setDescription('جلب بانر ديسكورد عريض متحرك ومضمون 100%')
    .addStringOption(opt =>
      opt.setName('search_term')
        .setDescription('أدخل موضوع البانر (anime, lofi, gaming, cyberpunk, nature...)')
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
  console.log('🌟 High-Speed Local JSON Banner Bot ready.');
  readyClient.user.setActivity('/banner [search_term]', { type: 2 });
  await registerCommands();
});

client.on('interactionCreate', async interaction => {
  try {
    // ─── Slash Command /banner ─────────────────────────────────────────────
    if (interaction.isChatInputCommand() && interaction.commandName === 'banner') {
      const searchTerm = interaction.options.getString('search_term', true);
      await interaction.deferReply();

      const bannerData = getBannerByCategory(searchTerm);
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
            .setTitle(`📌 ${embed.title || 'Discord Banner'}`)
            .setImage(embed.image.url)
            .setColor(0x5865f2)
            .setDescription(`محفوظ من **${interaction.guild?.name || 'Discord'}** في <#${interaction.channelId}>`)
            .setFooter({ text: 'Discord Banner Bot' })
            .setTimestamp();
          await interaction.user.send({ embeds: [dmEmbed] });
          await interaction.editReply({ content: '✅ تم إرسال البانر إلى رسائلك الخاصة!' });
        } catch {
          await interaction.editReply({ content: '❌ تعذر الإرسال! تأكد من السماح بالرسائل الخاصة في إعدادات السيرفر.' });
        }
        return;
      }

      // 🔄 Another Banner
      if (action === 'banner_another') {
        await interaction.deferUpdate();
        const data = getBannerByCategory(term || 'anime');
        await interaction.editReply({
          embeds: [createBannerEmbed(data, interaction.user)],
          components: [createBannerRow(term || 'anime', interaction.user.id)]
        });
        return;
      }

      // 🎲 Surprise Banner
      if (action === 'banner_surprise') {
        await interaction.deferUpdate();
        const data = getSurpriseBanner();
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
