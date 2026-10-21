# 🎬 Unlimited GIPHY Discord Bot (Discord.js v14)

A production-ready Discord bot delivering unlimited GIFs using the Giphy API with **zero-failure multi-tier fallback** and full interactive button support.

---

## ✨ Features

- **Slash Command (`/gif [search_term]`)**: Search any keyword, emotion, or phrase.
- **🛡️ Zero-Failure Architecture**:
  1. Primary query search with randomized offset (delivers fresh results every time).
  2. If offset yields no results, falls back to top results.
  3. If no match is found, queries Giphy's random endpoint using the tag.
  4. If query is obscure/gibberish, falls back to curated reaction keywords (`reaction`, `vibes`, `party`, etc.).
  5. If search API fails or rate-limits, falls back to Giphy Trending.
  6. Ultimate emergency high-availability fallback CDN link ensures the bot **never crashes or returns an empty response**.
- **Interactive Action Buttons**:
  - `🔄 Another One`: Immediately fetches and updates the message with another fresh GIF for the same search term.
  - `🎲 Surprise Me`: Fetches a fresh trending or surprise GIF.
  - `📌 Save`: Securely delivers the GIF directly to the user's private Direct Messages (DM).

---

## 📁 Project Structure

```text
GIF/
├── src/
│   ├── commands/
│   │   └── gif.js              # Slash command definition and execution
│   ├── handlers/
│   │   └── buttonHandler.js    # Button handlers ("Another One", "Surprise Me", "Save")
│   ├── services/
│   │   └── giphyService.js     # Giphy API integration & 5-tier fallback engine
│   ├── utils/
│   │   └── gifEmbed.js         # Embed generator and action row builders
│   ├── deploy-commands.js      # Slash command registration script (REST API)
│   └── index.js                # Main bot client entry point
├── .env.example                # Template for environment credentials
├── package.json                # Project dependencies and npm scripts
└── README.md                   # Full setup and deployment guide
```

---

## 🚀 Setup & Installation Guide

### Step 1: Prerequisites
- Install **Node.js (v18.0.0 or higher)**: [nodejs.org](https://nodejs.org/)
- Verify installation in your terminal:
  ```bash
  node -v
  npm -v
  ```

---

### Step 2: Get API Keys & Credentials

#### A. Discord Bot Token & Client ID
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, give it a name (e.g., `Giphy Bot`), and click **Create**.
3. Under **General Information**, copy the **Application ID** (this is your `CLIENT_ID`).
4. Go to the **Bot** tab on the left menu:
   - Click **Add Bot** (if not already added).
   - Click **Reset Token** and copy your **Bot Token** (this is your `DISCORD_TOKEN`).
5. In the **OAuth2 -> URL Generator** tab:
   - Select scopes: `bot`, `applications.commands`.
   - Select bot permissions: `Send Messages`, `Embed Links`, `Attach Files`, `Use External Emojis`, `Read Message History`.
   - Copy the generated URL and open it in your browser to invite the bot to your Discord server.

#### B. Giphy API Key
1. Go to the [Giphy Developers Portal](https://developers.giphy.com/).
2. Log in or create a free account.
3. Click **Create an SDK/API Key** -> Select **API** -> Click **Next Step**.
4. Give your app a name (e.g. `DiscordGifBot`) and click **Create New Key**.
5. Copy your **GIPHY API Key**.

---

### Step 3: Configure Environment Variables

1. In the project directory, duplicate `.env.example` and rename it to `.env`:
   ```bash
   cp .env.example .env
   ```
   *(On Windows Command Prompt / PowerShell, you can run `copy .env.example .env`)*

2. Open `.env` and paste your credentials:
   ```env
   DISCORD_TOKEN=your_actual_bot_token_here
   CLIENT_ID=your_actual_client_id_here
   GIPHY_API_KEY=your_actual_giphy_api_key_here
   GUILD_ID=your_test_server_id_here
   ```
   > 💡 **Tip for `GUILD_ID`**: Providing a Discord Server (Guild) ID allows slash commands to appear **instantly** in that server for testing. Leaving it blank registers the command **globally** across all servers (takes up to 1 hour to propagate).

---

### Step 4: Install Dependencies

Run the following command in the project root:

```bash
npm install
```

This installs `discord.js`, `axios`, and `dotenv`.

---

### Step 5: Register Slash Commands

Deploy the `/gif` command to Discord:

```bash
npm run deploy-commands
```

You should see output similar to:
```text
🚀 Refreshing 1 application (/) commands...
🎯 Registering slash commands specifically to Guild ID: 123456789...
✅ Application (/) commands registered successfully!
```

---

### Step 6: Start the Bot

Run the bot:

```bash
npm start
```

Output:
```text
🤖 Logged in as Giphy Bot#1234!
🌟 GIF Bot ready to serve unlimited GIFs.
```

Now jump into your Discord server and try typing `/gif cats`!

---

## 🛠️ Production Deployment Options

### Using PM2 (Process Manager)
To run the bot in the background continuously on a VPS or cloud server:

```bash
npm install -g pm2
pm2 start src/index.js --name "giphy-bot"
pm2 save
pm2 startup
```

### Docker (Optional)
You can containerize this bot by creating a simple `Dockerfile`:
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
CMD ["node", "src/index.js"]
```
