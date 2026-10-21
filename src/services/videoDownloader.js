import axios from 'axios';

/**
 * Universal video downloader service for TikTok, YouTube, Reels, Twitter/X, Pinterest
 */
export const videoDownloaderService = {
  /**
   * Resolve and fetch direct downloadable media URL
   * @param {string} rawUrl 
   */
  async resolveMedia(rawUrl) {
    const url = rawUrl.trim();

    // Check TikTok
    if (/tiktok\.com/i.test(url)) {
      return await this._downloadTikTok(url);
    }

    // Check Instagram Reels / Posts
    if (/instagram\.com\/(reel|p|tv)\//i.test(url)) {
      return await this._downloadInstagram(url);
    }

    // Check Twitter / X
    if (/twitter\.com|x\.com/i.test(url)) {
      return await this._downloadTwitter(url);
    }

    // Check YouTube / Shorts
    if (/youtube\.com|youtu\.be/i.test(url)) {
      return await this._downloadYouTube(url);
    }

    // Fallback: general stream resolver
    return await this._fallbackResolver(url);
  },

  /**
   * TikTok Downloader (using TikWM reliable API)
   */
  async _downloadTikTok(url) {
    try {
      const response = await axios.post(
        'https://www.tikwm.com/api/',
        new URLSearchParams({ url, count: 12, cursor: 0, web: 1, hd: 1 }),
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
          },
          timeout: 15000
        }
      );

      const data = response.data;
      if (data && data.code === 0 && data.data) {
        const videoData = data.data;
        const playUrl = videoData.hdplay || videoData.play || videoData.wmplay;
        return {
          success: true,
          title: videoData.title || 'TikTok Video',
          author: videoData.author?.nickname || videoData.author?.unique_id || 'TikTok User',
          downloadUrl: playUrl,
          thumbnail: videoData.cover,
          duration: videoData.duration || 0,
          platform: 'TikTok'
        };
      }
      throw new Error(data.msg || 'لم يتم العثور على المقطع عبر TikWM');
    } catch (err) {
      // Secondary fallback for TikTok via Cobalt API
      return await this._cobaltDownload(url, 'TikTok');
    }
  },

  /**
   * Instagram Downloader
   */
  async _downloadInstagram(url) {
    try {
      return await this._cobaltDownload(url, 'Instagram');
    } catch (err) {
      throw new Error(`تعذر تنزيل مقطع إنستغرام: ${err.message}`);
    }
  },

  /**
   * Twitter / X Downloader
   */
  async _downloadTwitter(url) {
    try {
      return await this._cobaltDownload(url, 'Twitter / X');
    } catch (err) {
      throw new Error(`تعذر تنزيل مقطع تويتر: ${err.message}`);
    }
  },

  /**
   * YouTube / Shorts Downloader
   */
  async _downloadYouTube(url) {
    try {
      return await this._cobaltDownload(url, 'YouTube');
    } catch (err) {
      throw new Error(`تعذر تنزيل مقطع يوتيوب: ${err.message}`);
    }
  },

  /**
   * Cobalt universal API fallback
   */
  async _cobaltDownload(url, platform = 'Video') {
    const instances = [
      'https://api.cobalt.tools',
      'https://cobalt.api.kwiatekm.tokyo',
      'https://co.wuk.sh'
    ];

    let lastError = null;

    for (const instance of instances) {
      try {
        const res = await axios.post(
          `${instance}/`,
          {
            url: url,
            videoQuality: '720',
            filenamePattern: 'nerd'
          },
          {
            headers: {
              'Accept': 'application/json',
              'Content-Type': 'application/json',
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) VisualVerseBot/1.0'
            },
            timeout: 12000
          }
        );

        if (res.data) {
          if (res.data.status === 'stream' || res.data.status === 'redirect' || res.data.status === 'tunnel') {
            return {
              success: true,
              title: `${platform} Video`,
              author: platform,
              downloadUrl: res.data.url,
              platform: platform
            };
          }
          if (res.data.status === 'picker' && res.data.picker?.length > 0) {
            const first = res.data.picker[0];
            return {
              success: true,
              title: `${platform} Media`,
              author: platform,
              downloadUrl: first.url,
              platform: platform
            };
          }
        }
      } catch (e) {
        lastError = e;
      }
    }

    throw new Error(lastError?.response?.data?.text || lastError?.message || 'تعذر معالجة رابط المقطع حالياً');
  },

  /**
   * General stream buffer downloader for sending directly to Discord chat
   * Checks max size limit (Discord limit is ~10MB for free bots / 25MB standard)
   */
  async downloadBuffer(downloadUrl, maxSizeMB = 24) {
    const response = await axios({
      method: 'GET',
      url: downloadUrl,
      responseType: 'arraybuffer',
      timeout: 30000,
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      },
      maxContentLength: maxSizeMB * 1024 * 1024
    });

    const buffer = Buffer.from(response.data);
    const sizeMB = (buffer.length / (1024 * 1024)).toFixed(2);

    return {
      buffer,
      sizeMB,
      contentType: response.headers['content-type'] || 'video/mp4'
    };
  }
};

export default videoDownloaderService;
