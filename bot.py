import os
import sys
import json
import random
import asyncio
import aiohttp
from aiohttp import web
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_TOKEN")
UNSPLASH_API_KEY = os.getenv("UNSPLASH_API_KEY", "")
PORT = int(os.getenv("PORT", 8080))


async def run_web_server():
    """خادم ويب خفيف لإبقاء الخدمة نشطة ومتوافقة مع Render"""
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="TwinAura Matching Bot is Online!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 خادم الويب يعمل على المنفذ: {PORT}")


# فئات الأطقم المتناسقة مع تاغات مضمونة 100%
CATEGORIES = {
    "أنمي": {
        "unsplash": "anime girl aesthetic",
        "avatar_tag": "1girl rating:general",
        "banner_tag": "scenery rating:general"
    },
    "استاتيك": {
        "unsplash": "minimalist aesthetic wallpaper",
        "avatar_tag": "solo rating:general",
        "banner_tag": "clouds scenery rating:general"
    },
    "داكن": {
        "unsplash": "dark purple aesthetic",
        "avatar_tag": "purple_theme rating:general",
        "banner_tag": "dark scenery rating:general"
    },
    "لطيف": {
        "unsplash": "cute pastel anime",
        "avatar_tag": "cat rating:general",
        "banner_tag": "sky rating:general"
    }
}


async def fetch_matching_pairs(category: str, limit: int = 10) -> list[dict]:
    """
    جلب أزواج متناسقة مضمونة (أفاتار + بنر).
    """
    cat_cfg = CATEGORIES.get(category, CATEGORIES["أنمي"])
    pairs = []

    # 1. إذا كان لدى المستخدم مفتاح Unsplash صالح
    if UNSPLASH_API_KEY and UNSPLASH_API_KEY != "YOUR_UNSPLASH_API_KEY":
        query = cat_cfg["unsplash"]
        url = f"https://api.unsplash.com/search/photos?query={query}&client_id={UNSPLASH_API_KEY}&per_page={limit*2}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        for i in range(0, len(results) - 1, 2):
                            avatar_url = results[i]["urls"]["regular"]
                            banner_url = results[i+1]["urls"]["regular"]
                            pairs.append({"avatar": avatar_url, "banner": banner_url})
                        if pairs:
                            return pairs
        except Exception as e:
            print(f"[Unsplash warning]: {e}")

    # 2. المصدر المباشر السريع (مجاني وبدون مفاتيح ونتائج فورية)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        pid_a = random.randint(0, 10)
        pid_b = random.randint(0, 10)
        url_av = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&tags={cat_cfg['avatar_tag'].replace(' ', '+')}&limit={limit}&pid={pid_a}"
        url_bn = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&tags={cat_cfg['banner_tag'].replace(' ', '+')}&limit={limit}&pid={pid_b}"

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            async with session.get(url_av, headers=headers) as r_a, session.get(url_bn, headers=headers) as r_b:
                if r_a.status == 200 and r_b.status == 200:
                    data_a = await r_a.json()
                    data_b = await r_b.json()
                    min_len = min(len(data_a), len(data_b))
                    for i in range(min_len):
                        img_a = str(data_a[i].get("image", ""))
                        img_b = str(data_b[i].get("image", ""))
                        if not img_a.lower().endswith(".gif") and not img_b.lower().endswith(".gif"):
                            pairs.append({
                                "avatar": f"https://safebooru.org/images/{data_a[i]['directory']}/{img_a}",
                                "banner": f"https://safebooru.org/images/{data_b[i]['directory']}/{img_b}"
                            })
    except Exception as e:
        print(f"[Fetch pairs exception]: {e}")

    return pairs


# ==================== كلاس الأزرار التفاعلية (Pagination) ====================
class MatchingView(discord.ui.View):
    def __init__(self, pairs: list[dict], category: str):
        super().__init__(timeout=180)
        self.pairs = pairs
        self.category = category
        self.index = 0
        self.update_buttons()

    def update_buttons(self):
        self.prev_button.disabled = (self.index == 0)
        self.next_button.disabled = (self.index >= len(self.pairs) - 1)

    def update_embed(self) -> discord.Embed:
        pair = self.pairs[self.index]
        embed = discord.Embed(
            title="✨ طقم أفاتار وبنر متناسقين (Matching Set)",
            description=f"التصنيف: **{self.category}** • الزوج **{self.index + 1}** من أصل **{len(self.pairs)}**\n"
                        f"*(الأفاتار في الصورة المصغرة 👤 والبنر في الصورة العريضة 🖼️)*",
            color=discord.Color.from_rgb(114, 137, 218)
        )
        embed.set_thumbnail(url=pair.get("avatar"))
        embed.set_image(url=pair.get("banner"))
        embed.add_field(name="🖼️ تحميل الأفاتار", value=f"[اضغط هنا للتحميل]({pair.get('avatar')})", inline=True)
        embed.add_field(name="🌆 تحميل البنر", value=f"[اضغط هنا للتحميل]({pair.get('banner')})", inline=True)
        embed.set_footer(text="TwinAura Bot • Matching Profiles • دقة عالية HD")
        return embed

    @discord.ui.button(label="السابق", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="التالي", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pairs) - 1:
            self.index += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="إغلاق", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


# ==================== إعدادات وتشغيل البوت ====================
class TwinAuraBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            await run_web_server()
        except Exception as e:
            print(f"⚠️ تنبيه خادم الويب: {e}")
        try:
            synced = await self.tree.sync()
            print(f"✅ تم مزامنة {len(synced)} أمر تفاعلي بنجاح.")
        except Exception as e:
            print(f"❌ خطأ أثناء المزامنة: {e}")


bot = TwinAuraBot()


@bot.event
async def on_ready():
    print(f"🤖 البوت يعمل بنجاح باسم: {bot.user.name}")


# ==================== أمر الـ Slash Command الرئيسي ====================
@bot.tree.command(name="matching", description="جلب أفاتار وبنر متناسقين للملف الشخصي بحسب الفئة")
@app_commands.describe(category="اختر الفئة المطلوبة")
@app_commands.choices(category=[
    app_commands.Choice(name="أنمي", value="أنمي"),
    app_commands.Choice(name="استاتيك", value="استاتيك"),
    app_commands.Choice(name="داكن", value="داكن"),
    app_commands.Choice(name="لطيف", value="لطيف")
])
async def matching_command(interaction: discord.Interaction, category: str):
    # إشعار ديسكورد فوراً بالانتظار لمنع رسالة The application did not respond
    await interaction.response.defer(thinking=True)

    try:
        pairs = await fetch_matching_pairs(category, limit=10)

        if not pairs:
            await interaction.followup.send("⚠️ لم يتم العثور على أزواج متناسقة حالياً، يرجى المحاولة بعد قليل.", ephemeral=True)
            return

        view = MatchingView(pairs, category)
        embed = view.update_embed()
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"[Error in matching_command]: {e}")
        await interaction.followup.send("❌ حدث خطأ أثناء معالجة الطلب، يرجى المحاولة مرة أخرى.", ephemeral=True)


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ خطأ: لم يتم العثور على DISCORD_TOKEN في ملف .env")
    else:
        bot.run(BOT_TOKEN)
