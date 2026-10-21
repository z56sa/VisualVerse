/**
 * generate_assets.js
 * Generates beautiful, styled local SVG avatars & banners for all pairs
 */

const fs = require('fs');
const path = require('path');

const imgDir = path.join(__dirname, 'public', 'images');
if (!fs.existsSync(imgDir)) {
  fs.mkdirSync(imgDir, { recursive: true });
}

const data = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'matching.json'), 'utf8'));

// Palette themes
const themes = {
  anime: [
    { bg1: '#1e1b4b', bg2: '#4338ca', accent: '#818cf8', sym: '⚔️' },
    { bg1: '#311042', bg2: '#831843', accent: '#f43f5e', sym: '⚡' },
    { bg1: '#142930', bg2: '#0e7490', accent: '#38bdf8', sym: '🌊' },
    { bg1: '#3b0764', bg2: '#6d28d9', accent: '#a855f7', sym: '🔥' }
  ],
  gaming: [
    { bg1: '#022c22', bg2: '#047857', accent: '#34d399', sym: '🎯' },
    { bg1: '#172554', bg2: '#1d4ed8', accent: '#60a5fa', sym: '🎮' },
    { bg1: '#2e1065', bg2: '#7c3aed', accent: '#c084fc', sym: '🏆' }
  ],
  couples: [
    { bg1: '#4a044e', bg2: '#9d174d', accent: '#fb7185', sym: '💖' },
    { bg1: '#18181b', bg2: '#3f3f46', accent: '#f472b6', sym: '✨' }
  ],
  aesthetic: [
    { bg1: '#262626', bg2: '#404040', accent: '#facc15', sym: '🌙' },
    { bg1: '#451a03', bg2: '#9a3412', accent: '#fb923c', sym: '🌅' },
    { bg1: '#1c1917', bg2: '#44403c', accent: '#d6d3d1', sym: '📜' }
  ]
};

function createAvatarSvg(label, theme, subText) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="100%" height="100%">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="${theme.bg1}"/>
      <stop offset="100%" stop-color="${theme.bg2}"/>
    </linearGradient>
    <filter id="glow">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="${theme.accent}" flood-opacity="0.35"/>
    </filter>
  </defs>
  <rect width="400" height="400" fill="url(#grad)" rx="32"/>
  <circle cx="200" cy="160" r="90" fill="none" stroke="${theme.accent}" stroke-width="4" stroke-dasharray="8 8" opacity="0.6"/>
  <circle cx="200" cy="160" r="75" fill="${theme.bg1}" filter="url(#glow)"/>
  <text x="200" y="180" font-family="'Cairo', sans-serif, 'Segoe UI Emoji'" font-size="64" text-anchor="middle" fill="#ffffff">${theme.sym}</text>
  <text x="200" y="290" font-family="'Cairo', sans-serif" font-weight="bold" font-size="28" text-anchor="middle" fill="#ffffff">${label}</text>
  <text x="200" y="325" font-family="'Cairo', sans-serif" font-size="16" text-anchor="middle" fill="${theme.accent}" opacity="0.9">${subText}</text>
</svg>`;
}

function createBannerSvg(title, theme, category) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="100%" height="100%">
  <defs>
    <linearGradient id="bgrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="${theme.bg1}"/>
      <stop offset="50%" stop-color="${theme.bg2}"/>
      <stop offset="100%" stop-color="${theme.bg1}"/>
    </linearGradient>
    <radialGradient id="sparkle" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="${theme.accent}" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="${theme.bg1}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="1200" height="400" fill="url(#bgrad)"/>
  <ellipse cx="600" cy="200" rx="400" ry="200" fill="url(#sparkle)"/>
  <circle cx="200" cy="200" r="140" fill="none" stroke="${theme.accent}" stroke-width="2" opacity="0.2"/>
  <circle cx="1000" cy="200" r="140" fill="none" stroke="${theme.accent}" stroke-width="2" opacity="0.2"/>
  <text x="600" y="140" font-family="'Cairo', sans-serif, 'Segoe UI Emoji'" font-size="52" text-anchor="middle">${theme.sym}</text>
  <text x="600" y="210" font-family="'Cairo', sans-serif" font-weight="900" font-size="42" text-anchor="middle" fill="#ffffff" letter-spacing="1">${title}</text>
  <text x="600" y="260" font-family="'Cairo', sans-serif" font-weight="bold" font-size="20" text-anchor="middle" fill="${theme.accent}" letter-spacing="4">MATCHING PROFILE BANNER • ${category.toUpperCase()}</text>
</svg>`;
}

let catCounters = {};

data.forEach((pair) => {
  const cat = pair.category;
  catCounters[cat] = (catCounters[cat] || 0);
  const themeList = themes[cat] || themes.aesthetic;
  const theme = themeList[catCounters[cat] % themeList.length];
  catCounters[cat]++;

  const av1File = `${pair.id}-avatar1.svg`;
  const av2File = `${pair.id}-avatar2.svg`;
  const bannerFile = `${pair.id}-banner.svg`;

  fs.writeFileSync(path.join(imgDir, av1File), createAvatarSvg(pair.avatar1.label, theme, 'DUO AVATAR 1'));
  fs.writeFileSync(path.join(imgDir, av2File), createAvatarSvg(pair.avatar2.label, theme, 'DUO AVATAR 2'));
  fs.writeFileSync(path.join(imgDir, bannerFile), createBannerSvg(pair.title, theme, pair.category));

  pair.avatar1.url = `/images/${av1File}`;
  pair.avatar2.url = `/images/${av2File}`;
  pair.banner.url = `/images/${bannerFile}`;
});

fs.writeFileSync(path.join(__dirname, 'data', 'matching.json'), JSON.stringify(data, null, 2), 'utf8');
console.log('Successfully generated local matching visual assets and updated matching.json!');
