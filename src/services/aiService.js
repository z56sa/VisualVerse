import { GoogleGenerativeAI } from '@google/generative-ai';

let genAI = null;

function getAIClient(apiKey) {
  if (!apiKey) return null;
  if (!genAI) {
    genAI = new GoogleGenerativeAI(apiKey);
  }
  return genAI;
}

/**
 * تلخيص ومعالجة الخبر باللغتين العربية أو الإنجليزية
 * @param {string} apiKey 
 * @param {string} title - عنوان الخبر
 * @param {string} content - محتوى الخبر
 * @param {'ar' | 'en'} lang - اللغة المطلوبة (العربية ar أو الإنجليزية en)
 * @returns {Promise<{ formattedTitle: string, summaryPoints: string[] }>}
 */
export async function summarizeNewsItem(apiKey, title, content, lang = 'ar') {
  const isArabic = lang === 'ar';

  // معالجة احتياطية سريعة إذا لم يتوفر مفتاح AI
  if (!apiKey || apiKey.trim().length === 0) {
    const cleanSnippet = (content || title || '').replace(/<[^>]*>/g, '').trim();
    return {
      formattedTitle: title,
      summaryPoints: [
        cleanSnippet.slice(0, 160) + (cleanSnippet.length > 160 ? '...' : ''),
        isArabic ? 'اضغط على زر المصدر أدناه لقراءة التفاصيل الكاملة للخبر.' : 'Click the button below to read the full report.'
      ]
    };
  }

  try {
    const ai = getAIClient(apiKey);
    const model = ai.getGenerativeModel({ model: 'gemini-1.5-flash' });

    const prompt = isArabic
      ? `
أنت محرر إخباري محترف مسؤول عن بوت FeedPulse في ديسكورد.
مهمتك: قراءة الخبر التالي، ترجمة العنوان وصياغته بأسلوب عربي مشوق، وتلخيص الخبر في 3 نقاط محددة وسهلة القراءة ومباشرة باللغة العربية.

عنوان الخبر: ${title}
نص الخبر: ${content || 'لا يوجد نص إضافي'}

المطلوب إخراجه بهذا الشكل الصارم دون أي مقدمات:
العنوان: [عنوان عربي جذاب ومختصر]
- [النقطة الأولى]
- [النقطة الثانية]
- [النقطة الثالثة]
`
      : `
You are a professional news editor for the FeedPulse Discord bot.
Your task: Read the following news item, craft an engaging English headline, and summarize the key facts in 3 crisp, informative bullet points in English.

News Title: ${title}
News Content: ${content || 'No additional content'}

Output strictly in this format without introductory banter:
Title: [Catchy concise English title]
- [Key point 1]
- [Key point 2]
- [Key point 3]
`;

    const result = await model.generateContent(prompt);
    const responseText = result.response.text().trim();

    const lines = responseText.split('\n').map(l => l.trim()).filter(Boolean);
    let formattedTitle = title;
    const summaryPoints = [];

    for (const line of lines) {
      if (line.startsWith('العنوان:') || line.startsWith('Title:')) {
        formattedTitle = line.replace(/^(العنوان:|Title:)\s*/, '').trim();
      } else if (line.startsWith('-') || line.startsWith('•') || line.startsWith('*')) {
        summaryPoints.push(line.replace(/^[-•*]\s*/, '').trim());
      }
    }

    if (summaryPoints.length === 0) {
      summaryPoints.push(responseText.slice(0, 300));
    }

    return {
      formattedTitle: formattedTitle || title,
      summaryPoints: summaryPoints.slice(0, 3)
    };
  } catch (error) {
    console.warn('⚠️ AI Summarization fallback triggered:', error.message);
    const cleanSnippet = (content || title || '').replace(/<[^>]*>/g, '').trim();
    return {
      formattedTitle: title,
      summaryPoints: [
        cleanSnippet.slice(0, 160) + '...',
        isArabic ? 'اضغط على الرابط بالأسفل للاطلاع على التقرير الكامل.' : 'Click the button below to view the full report.'
      ]
    };
  }
}

/**
 * توليد ملخص إخباري يومي شامل (عربي أو إنجليزي)
 * @param {string} apiKey 
 * @param {Array<{ title: string, source: string }>} newsItems 
 * @param {'ar' | 'en'} lang 
 * @returns {Promise<string>}
 */
export async function generateDailyRecap(apiKey, newsItems) {
  return generateDailyRecapWithLang(apiKey, newsItems, 'ar');
}

export async function generateDailyRecapWithLang(apiKey, newsItems, lang = 'ar') {
  const isArabic = lang === 'ar';

  if (!apiKey || apiKey.trim().length === 0 || !Array.isArray(newsItems) || newsItems.length === 0) {
    return isArabic
      ? '📊 **نشرة FeedPulse الإخبارية اليومية:**\n' + newsItems.map((n, i) => `${i + 1}. **${n.title}** (${n.source})`).join('\n')
      : '📊 **FeedPulse Daily News Brief:**\n' + newsItems.map((n, i) => `${i + 1}. **${n.title}** (${n.source})`).join('\n');
  }

  try {
    const ai = getAIClient(apiKey);
    const model = ai.getGenerativeModel({ model: 'gemini-1.5-flash' });

    const newsListText = newsItems.map((n, i) => `${i + 1}. ${n.title} [Source: ${n.source}]`).join('\n');

    const prompt = isArabic
      ? `أنت محرر إخباري. إليك قائمة بأهم الأخبار اليومية:\n${newsListText}\nقم بصياغة نشرة موجزة بعنوان "⚡ حصاد اليوم من FeedPulse" تلخص أهم الاتجاهات والأحداث في 4 إلى 5 نقاط رئيسية بالعربية بأسلوب إعلامي شيق.`
      : `You are an executive news editor. Here is today's top news list:\n${newsListText}\nCraft a concise daily brief titled "⚡ FeedPulse Daily Highlights" summarizing the biggest trends and stories in 4 to 5 bullet points in English.`;

    const result = await model.generateContent(prompt);
    return result.response.text().trim();
  } catch (err) {
    console.warn('Daily recap AI error:', err.message);
    return isArabic
      ? '📊 **نشرة FeedPulse الإخبارية اليومية:**\n' + newsItems.map((n, i) => `🔹 **${n.title}** (${n.source})`).join('\n')
      : '📊 **FeedPulse Daily News Brief:**\n' + newsItems.map((n, i) => `🔹 **${n.title}** (${n.source})`).join('\n');
  }
}
