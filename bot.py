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

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 8080))

SAFEBOORU = "https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1"

# ======== تصنيفات الافتارات ========
AVATAR_CATEGORIES = {
    "anime_boy": {
        "label": "أنمي أولاد (Anime Boy PFP)",
        "tags": "1boy solo -animated",
        "color": discord.Color.blue(),
        "emoji": "👦"
    },
    "anime_girl": {
        "label": "أنمي بنات (Anime Girl PFP)",
        "tags": "1girl solo -animated",
        "color": discord.Color.magenta(),
        "emoji": "👧"
    },
    "dark_purple": {
        "label": "دارك وبنفسجي (Dark / Purple)",
        "tags": "1girl solo purple_hair dark -animated",
        "color": discord.Color.dark_purple(),
        "emoji": "🖤"
    },
    "cyberpunk": {
        "label": "سايبربانك ونيون (Cyberpunk / Neon)",
        "tags": "cyberpunk solo -animated",
        "color": discord.Color.teal(),
        "emoji": "🌆"
    },
    "couple": {
        "label": "صور طقم (Matching Couple)",
        "tags": "2girls -animated",
        "color": discord.Color.fuchsia(),
        "emoji": "✨"
    },
    "cat_cute": {
        "label": "قطط كيوت (Cute Cats)",
        "tags": "cat 1girl solo -animated",
        "color": discord.Color.orange(),
        "emoji": "🐱"
    }
}

# ======== تصنيفات البنرات ========
BANNER_CATEGORIES = {
    "dark_purple_scene": {
        "label": "دارك وبنفسجي (Dark Purple Scene)",
        "tags": "scenery purple -animated",
        "color": discord.Color.purple(),
        "emoji": "🌌"
    },
    "anime_landscape": {
        "label": "مناظر أنمي (Anime Landscape)",
        "tags": "scenery sky anime -animated",
        "color": discord.Color.blue(),
        "emoji": "🌸"
    },
    "cyberpunk_city": {
        "label": "سايبربانك ومدينة (Cyberpunk City)",
        "tags": "cyberpunk scenery -animated",
        "color": discord.Color.teal(),
        "emoji": "🌆"
    },
    "space_galaxy": {
        "label": "فضاء ومجرات (Space / Galaxy)",
        "tags": "space scenery sky -animated",
        "color": discord.Color.dark_blue(),
        "emoji": "🪐"
    },
    "forest_nature": {
        "label": "طبيعة وغابات (Forest / Nature)",
        "tags": "forest scenery nature -animated",
        "color": discord.Color.green(),
        "emoji": "🌿"
    },
    "pixel_lofi": {
        "label": "بكسل ولوفاي (Pixel / Lofi)",
        "tags": "pixel_art scenery -animated",
        "color": discord.Color.greyple(),
        "emoji": "🎮"
    }
}


async def run_web_server():
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="VisualVerse Bot is Online!"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Web server running on port {PORT}")


async def fetch_images(tags: str, limit: int = 20) -> list[dict]:
    """
    يجلب صور HD ثابتة (JPG/PNG فقط) من Safebooru
    """
    clean = "+".join(tags.strip().split())
    pid = random.randint(0, 5)
    url = f"{SAFEBOORU}&tags={clean}&limit={limit}&pid={pid}"

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    return []
                text = await resp.text()
                if not text.strip() or text.strip() == "[]":
                    # Fallback: pid=0
                    fallback = f"{SAFEBOORU}&tags={clean}&limit={limit}&pid=0"
                    async with session.get(fallback, headers=headers) as r2:
                        text = await r2.text()
                        if not text.strip():
                            return []

                data = json.loads(text)
                results = []
                for item in data:
                    img_file = str(item.get("image", ""))
                    # استثناء الـ GIF بشكل صارم ✅
                    if img_file.lower().endswith(".gif"):
                        continue
                    d = str(item.get("directory", ""))
                    if d and img_file:
                        img_url = f"https://safebooru.org/images/{d}/{img_file}"
                        results.append({
                            "url": img_url,
                            "tags": str(item.get("tags", ""))[:120]
                        })
                return results
        except Exception as e:
            print(f"[Fetch Error] {e}")
            return []


class BrowseView(discord.ui.View):
    """
    عرض الصور مع أزرار التنقل ورابط التحميل المباشر
    """
    def __init__(self, images: list[dict], title: str, color: discord.Color, requester: discord.User | discord.Member):
        super().__init__(timeout=300)
        self.images = images
        self.title = title
        self.color = color
        self.requester = requester
        self.index = 0
        self._update_buttons()

    def _update_buttons(self):
        self.btn_prev.disabled = self.index == 0
        self.btn_next.disabled = self.index >= len(self.images) - 1

    def build_embed(self) -> discord.Embed:
        img = self.images[self.index]
        embed = discord.Embed(
            title=f"🎨 {self.title}",
            description=f"**[🔗 تحميل الصورة بجودة كاملة (HD)]({img['url']})**\n"
                        f"انقر على الرابط → ثم اضغط `Save image as...` لحفظها 📥",
            color=self.color
        )
        embed.set_image(url=img["url"])
        embed.set_footer(
            text=f"الصورة {self.index + 1} من {len(self.images)} • طلب بواسطة {self.requester.display_name}",
            icon_url=self.requester.display_avatar.url
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.requester.id:
            await interaction.response.send_message("❌ هذه الأزرار للشخص الذي طلب الأمر فقط!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀️ السابق", style=discord.ButtonStyle.secondary)
    async def btn_prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="التالي ▶️", style=discord.ButtonStyle.primary)
    async def btn_next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🔀 صور جديدة", style=discord.ButtonStyle.success)
    async def btn_refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        # إعادة جلب صور جديدة عشوائية
        new_imgs = await fetch_images(self._tags, 20)
        if new_imgs:
            self.images = new_imgs
            self.index = 0
            self._update_buttons()
        await interaction.edit_original_response(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🗑️ إغلاق", style=discord.ButtonStyle.danger)
    async def btn_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class CategorySelect(discord.ui.Select):
    def __init__(self, categories: dict, section: str, user: discord.User | discord.Member):
        self.categories = categories
        self.section = section
        self.user = user

        options = [
            discord.SelectOption(label=v["label"], value=k, emoji=v["emoji"])
            for k, v in categories.items()
        ]
        placeholder = "اختر تصنيف الافتار..." if section == "avatar" else "اختر تصنيف البنر..."
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ هذه القائمة للشخص الطالب فقط!", ephemeral=True)
            return

        key = self.values[0]
        cat = self.categories[key]
        await interaction.response.defer()

        imgs = await fetch_images(cat["tags"], 20)
        if not imgs:
            await interaction.followup.send("⚠️ لم يتم إيجاد صور حالياً. حاول مرة أخرى!", ephemeral=True)
            return

        view = BrowseView(images=imgs, title=cat["label"], color=cat["color"], requester=self.user)
        view._tags = cat["tags"]  # حفظ التاقات لزر "صور جديدة"
        await interaction.edit_original_response(embed=view.build_embed(), view=view)


class CategoryView(discord.ui.View):
    def __init__(self, categories: dict, section: str, user: discord.User | discord.Member):
        super().__init__(timeout=60)
        self.add_item(CategorySelect(categories, section, user))


intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    try:
        await run_web_server()
    except Exception as e:
        print(f"⚠️ Web server warning: {e}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Sync error: {e}")
    print(f"🤖 Bot ready as: {bot.user}")


@bot.tree.command(name="avatar", description="تصفح افتارات أنمي جمالية جاهزة للاستخدام كصور HD ثابتة")
async def slash_avatar(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👤 تصفح الافتارات الجمالية",
        description="اختر التصنيف المناسب لعرض مجموعة من الافتارات الأنمي الجمالية بجودة HD جاهزة للاستخدام:",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="جميع الصور ثابتة PNG/JPG عالية الجودة 🖼️")
    await interaction.response.send_message(
        embed=embed,
        view=CategoryView(AVATAR_CATEGORIES, "avatar", interaction.user)
    )


@bot.tree.command(name="banner", description="تصفح بنرات وهيدرات جمالية جاهزة للاستخدام كصور HD عريضة")
async def slash_banner(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🖼️ تصفح البنرات الجمالية",
        description="اختر التصنيف المناسب لعرض مجموعة من البنرات والهيدرات الجمالية الواسعة بجودة HD جاهزة للاستخدام:",
        color=discord.Color.dark_purple()
    )
    embed.set_footer(text="جميع الصور ثابتة PNG/JPG عالية الجودة 🖼️")
    await interaction.response.send_message(
        embed=embed,
        view=CategoryView(BANNER_CATEGORIES, "banner", interaction.user)
    )


@bot.tree.command(name="help", description="دليل أوامر بوت VisualVerse")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✨ دليل أوامر VisualVerse",
        description="بوت لتصفح وتحميل افتارات وبنرات أنمي جمالية ثابتة HD جاهزة لحسابك:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="👤 `/avatar`",
        value="تصفح افتارات أنمي جمالية (أولاد، بنات، دارك، سايبربانك، أطقم، قطط) واحفظ ما يعجبك.",
        inline=False
    )
    embed.add_field(
        name="🖼️ `/banner`",
        value="تصفح بنرات وهيدرات واسعة جمالية (دارك بنفسجي، مناظر أنمي، سايبربانك، فضاء، طبيعة، لوفاي بكسل).",
        inline=False
    )
    embed.add_field(
        name="🔀 زر (صور جديدة)",
        value="في كل تصنيف يمكنك الضغط على زر **🔀 صور جديدة** للحصول على مجموعة مختلفة من الصور.",
        inline=False
    )
    embed.set_footer(text="كل الصور ثابتة PNG/JPG - لا GIFs. انقر على رابط التحميل لحفظ الصورة.")
    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Error: Please set DISCORD_TOKEN in .env")
    else:
        bot.run(DISCORD_TOKEN)
