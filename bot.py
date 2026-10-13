import os
import sys
import random
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

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 8080))


async def run_web_server():
    """خادم ويب خفيف لإبقاء الخدمة نشطة على Render"""
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="VisualVerse Aesthetic HD PFP & Banner Bot is Online!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 خادم الويب يعمل على المنفذ: {PORT}")


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# تصنيفات الافتارات الحقيقية الفخمة (صور HD حقيقية للبروفايل)
AVATAR_CATEGORIES = {
    "anime_boy": {
        "label": "أنمي أولاد فخم (Anime Boy)",
        "tags": "1boy solo aesthetic rating:general",
        "color": discord.Color.blue(),
        "emoji": "👦"
    },
    "anime_girl": {
        "label": "أنمي بنات جمالي (Anime Girl)",
        "tags": "1girl solo aesthetic rating:general",
        "color": discord.Color.purple(),
        "emoji": "👧"
    },
    "dark_purple": {
        "label": "دارك وبنفسجي (Dark / Purple Aesthetic)",
        "tags": "dark purple_theme solo rating:general",
        "color": discord.Color.dark_purple(),
        "emoji": "🖤"
    },
    "cyberpunk": {
        "label": "سايبربانك ونيون (Cyberpunk / Neon)",
        "tags": "cyberpunk neon solo rating:general",
        "color": discord.Color.teal(),
        "emoji": "🌆"
    },
    "matching": {
        "label": "افتارات طقم كبلز (Matching / Couple)",
        "tags": "2girls OR 1boy_1girl aesthetic rating:general",
        "color": discord.Color.fuchsia(),
        "emoji": "✨"
    },
    "cat_aesthetic": {
        "label": "قطط جمالية (Aesthetic Cats)",
        "tags": "cat aesthetic rating:general",
        "color": discord.Color.orange(),
        "emoji": "🐱"
    }
}

# تصنيفات البنرات الحقيقية للبروفايل (صور أفقية بنرات وهيدرات HD)
BANNER_CATEGORIES = {
    "dark_purple_banner": {
        "label": "بنر دارك وبنفسجي (Dark Purple Scenery)",
        "tags": "scenery purple_theme wallpaper rating:general",
        "color": discord.Color.purple(),
        "emoji": "🌌"
    },
    "anime_scenery": {
        "label": "بنر أنمي ومناظر (Anime Landscape)",
        "tags": "scenery sky clouds wallpaper rating:general",
        "color": discord.Color.magenta(),
        "emoji": "🌸"
    },
    "cyberpunk_city": {
        "label": "بنر سايبربانك ومدينة (Cyberpunk City)",
        "tags": "cyberpunk cityscape night wallpaper rating:general",
        "color": discord.Color.teal(),
        "emoji": "🌆"
    },
    "pixel_lofi": {
        "label": "بنر بكسل ولوفاي (Pixel / Lofi)",
        "tags": "pixel_art scenery wallpaper rating:general",
        "color": discord.Color.green(),
        "emoji": "🌿"
    },
    "space_galaxy": {
        "label": "بنر فضاء ومجرات (Space & Galaxy)",
        "tags": "space starry_sky scenery wallpaper rating:general",
        "color": discord.Color.dark_blue(),
        "emoji": "🪐"
    }
}


async def fetch_hd_images(tags: str, limit: int = 15) -> list[dict]:
    """
    جلب صور حقيقية عالية الدقة HD للافتارات والبنرات
    بدون أي API Key، وبشكل مجاني وسريع 100%.
    """
    clean_tags = "+".join(tags.strip().split())
    # اختيار صفحة عشوائية للحصول على نتائج جديدة ومنوعة في كل طلب
    random_pid = random.randint(0, 15)
    url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&tags={clean_tags}&limit={limit}&pid={random_pid}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for item in data:
                        d = str(item.get("directory", ""))
                        img = str(item.get("image", ""))
                        if d and img:
                            img_url = f"https://safebooru.org/images/{d}/{img}"
                            results.append({
                                "url": img_url,
                                "id": str(item.get("id", ""))
                            })
                    return results
                else:
                    return []
    except Exception as e:
        print(f"Error fetching HD images: {e}")
        return []


class ProfileMediaPaginationView(discord.ui.View):
    def __init__(self, items: list[dict], title: str, media_type: str, color: discord.Color, user: discord.User | discord.Member):
        super().__init__(timeout=180)
        self.items = items
        self.title = title
        self.media_type = media_type
        self.color = color
        self.user = user
        self.index = 0
        self.update_buttons()

    def update_buttons(self):
        self.btn_prev.disabled = (self.index == 0)
        self.btn_next.disabled = (self.index >= len(self.items) - 1)

    def create_embed(self) -> discord.Embed:
        current = self.items[self.index]
        icon = "👤 افتار" if self.media_type == "avatar" else "🖼️ بنر"
        embed = discord.Embed(
            title=f"{icon} | {self.title}",
            description=f"**[🔗 اضغط هنا لتحميل الصورة بجودة كاملة HD]({current['url']})**",
            color=self.color
        )
        embed.set_image(url=current["url"])
        embed.set_footer(
            text=f"الصورة {self.index + 1} من {len(self.items)} • تم الطلب بواسطة {self.user.display_name}",
            icon_url=self.user.display_avatar.url
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ هذه الأزرار خاصة بصاحب الطلب فقط!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀️ السابق", style=discord.ButtonStyle.secondary, custom_id="btn_prev")
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="التالي ▶️", style=discord.ButtonStyle.primary, custom_id="btn_next")
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.items) - 1:
            self.index += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="🗑️ إغلاق", style=discord.ButtonStyle.danger, custom_id="btn_delete")
    async def btn_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True


class CategorySelect(discord.ui.Select):
    def __init__(self, categories_dict: dict, media_type: str, user: discord.User | discord.Member):
        self.categories_dict = categories_dict
        self.media_type = media_type
        self.user = user

        options = [
            discord.SelectOption(
                label=data["label"],
                value=k,
                emoji=data["emoji"]
            )
            for k, data in categories_dict.items()
        ]
        placeholder = "اختر ستايل الافتار (Avatar PFP)..." if media_type == "avatar" else "اختر ستايل البنر (Profile Banner)..."
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ هذه القائمة خاصة بصاحب الطلب فقط!", ephemeral=True)
            return

        selected_key = self.values[0]
        cat_data = self.categories_dict[selected_key]

        await interaction.response.defer()

        items = await fetch_hd_images(cat_data["tags"], limit=15)
        if not items:
            await interaction.followup.send("⚠️ تعذر جلب الصور حالياً، يرجى المحاولة مرة أخرى.", ephemeral=True)
            return

        view = ProfileMediaPaginationView(
            items=items,
            title=cat_data["label"],
            media_type=self.media_type,
            color=cat_data["color"],
            user=self.user
        )
        await interaction.edit_original_response(embed=view.create_embed(), view=view)


class CategorySelectView(discord.ui.View):
    def __init__(self, categories_dict: dict, media_type: str, user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories_dict=categories_dict, media_type=media_type, user=user))


@bot.event
async def on_ready():
    try:
        await run_web_server()
    except Exception as e:
        print(f"⚠️ تنبيه خادم الويب: {e}")

    try:
        synced = await bot.tree.sync()
        print(f"✅ تم تسجيل {len(synced)} أمر بنجاح.")
    except Exception as e:
        print(f"❌ خطأ أثناء مزامنة الأوامر: {e}")
    print(f"🤖 البوت جاهز باسم: {bot.user}")


# أمر الافتارات
@bot.tree.command(name="avatar", description="تصفح افتارات (PFP) صور عالية الدقة HD للبروفايل")
@app_commands.describe(query="كلمة للبحث (اختياري، مثلاً: boy, girl, cat, dark)")
async def slash_avatar(interaction: discord.Interaction, query: str = None):
    if query:
        await interaction.response.defer()
        tags = f"{query} solo rating:general"
        items = await fetch_hd_images(tags, limit=15)
        if not items:
            await interaction.followup.send(f"⚠️ لم يتم العثور على افتارات لكلمة: **{query}**", ephemeral=True)
            return
        view = ProfileMediaPaginationView(
            items=items,
            title=f"افتارات: {query}",
            media_type="avatar",
            color=discord.Color.blue(),
            user=interaction.user
        )
        await interaction.followup.send(embed=view.create_embed(), view=view)
    else:
        embed = discord.Embed(
            title="👤 اختر تصنيف الافتار (Discord Avatar / PFP)",
            description="اختر الستايل المناسب لحسابك من القائمة لعرض صور حقيقية عالية الجودة (HD):",
            color=discord.Color.blurple()
        )
        view = CategorySelectView(categories_dict=AVATAR_CATEGORIES, media_type="avatar", user=interaction.user)
        await interaction.response.send_message(embed=embed, view=view)


# أمر البنرات
@bot.tree.command(name="banner", description="تصفح بنرات وهيدرات (Profile Banners) صور عريضة عالية الدقة HD")
@app_commands.describe(query="كلمة للبحث (اختياري، مثلاً: purple, anime, sky, city)")
async def slash_banner(interaction: discord.Interaction, query: str = None):
    if query:
        await interaction.response.defer()
        tags = f"{query} scenery wallpaper rating:general"
        items = await fetch_hd_images(tags, limit=15)
        if not items:
            await interaction.followup.send(f"⚠️ لم يتم العثور على بنرات لكلمة: **{query}**", ephemeral=True)
            return
        view = ProfileMediaPaginationView(
            items=items,
            title=f"بنرات: {query}",
            media_type="banner",
            color=discord.Color.purple(),
            user=interaction.user
        )
        await interaction.followup.send(embed=view.create_embed(), view=view)
    else:
        embed = discord.Embed(
            title="🖼️ اختر تصنيف البنر (Profile Banner / Header)",
            description="اختر نوع البنر المناسب لبروفايلك لعرض صور وهيدرات عريضة بجودة (HD):",
            color=discord.Color.dark_purple()
        )
        view = CategorySelectView(categories_dict=BANNER_CATEGORIES, media_type="banner", user=interaction.user)
        await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="help", description="دليل أوامر البوت")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ دليل أوامر VisualVerse",
        description="بوت مخصص لجلب افتارات بروفايل (PFP) وبنرات هيدر (Banners) بجودة صور حقيقية عالية الدقة HD:",
        color=discord.Color.gold()
    )
    embed.add_field(name="👤 `/avatar`", value="تصفح افتارات حقيقية للبروفايل (أنمي أولاد/بنات، دارك وبنفسجي، سايبربانك، أطقم، قطط).", inline=False)
    embed.add_field(name="🖼️ `/banner`", value="تصفح بنرات وهيدرات عريضة للبروفايل (دارك وبنفسجي، مناظر أنمي، سايبربانك، بكسل لوفاي، فضاء ومجرات).", inline=False)
    embed.set_footer(text="جميع الصور تدعم رابط مباشر للتحميل بجودة كاملة HD وأزرار تقليب.")
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ خطأ: يرجى وضع DISCORD_TOKEN في ملف .env")
    else:
        bot.run(DISCORD_TOKEN)
