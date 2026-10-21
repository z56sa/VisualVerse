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
 * تلخيص وترجمة الخبر بذكاء اصطناعي إلى اللغة العربية بأسلوب احترافي جذاب
 * @param {string} apiKey 
 * @param {string} title - عنوان الخبر
 * @param {string} content - نص الخبر أو مقتطف منه
 * @returns {Promise<{ arabicTitle: string, summaryPoints: string[] }>}
 */
export async function summarizeNewsItem(apiKey, title, content) {
  // إذا لم يتوفر مفتاح AI، نلخص بطريقة ذكية افتراضية
  if (!apiKey || apiKey.trim().length === 0) {
    const cleanSnippet = (content || title || '')
      .replace(/<[^>]*>/g, '')
      .trim();
    return {
      arabicTitle: title,
      summaryPoints: [
        cleanSnippet.slice(0, 150) + (cleanSnippet.length > 150 ? '...' : ''),
        'اضغط على زر المصدر أدناه لقراءة التفاصيل الكاملة للخبر.'
      ]
    };
  }

  try {
    const ai = getAIClient(apiKey);
    const model = ai.getGenerativeModel({ model: 'gemini-1.5-flash' });

    const prompt = `
أنت محرر إخباري محترف ومسؤول عن بوت FeedPulse في ديسكورد.
مهمتك: قراءة الخبر التالي، ترجمة العنوان وصياغته بأسلوب عربي مشوق، وتلخيص الخبر في 3 نقاط محددة وسهلة القراءة ومباشرة.

عنوان الخبر: ${title}
نص الخبر: ${content || 'لا يوجد نص إضافي'}

المطلوب إخراجه بهذا الشكل الصارم دون أي مقدمات أو كلام زائد:
العنوان: [عنوان عربي جذاب ومختصر]
- [النقطة الأولى]
- [النقطة الثانية]
- [النقطة الثالثة]
`;

    const result = await model.generateContent(prompt);
    const responseText = result.response.text().trim();

    const lines = responseText.split('\n').map(l => l.trim()).filter(Boolean);
    let arabicTitle = title;
    const summaryPoints = [];

    for (const line of lines) {
      if (line.startsWith('العنوان:')) {
        arabicTitle = line.replace('العنوان:', '').trim();
      } else if (line.startsWith('-') || line.startsWith('•') || line.startsWith('*')) {
        summaryPoints.push(line.replace(/^[-•*]\s*/, '').trim());
      }
    }

    if (summaryPoints.length === 0) {
      summaryPoints.push(responseText.slice(0, 300));
    }

    return {
      arabicTitle: arabicTitle || title,
      summaryPoints: summaryPoints.slice(0, 3)
    };
  } catch (error) {
    console.warn('⚠️ AI Summarization fallback triggered:', error.message);
    const cleanSnippet = (content || title || '').replace(/<[^>]*>/g, '').trim();
    return {
      arabicTitle: title,
      summaryPoints: [
        cleanSnippet.slice(0, 160) + '...',
        'اضغط على الرابط بالأسفل للاطلاع على التقرير الكامل.'
      ]
    };
  }
}

/**
 * توليد ملخص إخباري يومي شامل لمجموعة من الأخبار
 * @param {string} apiKey 
 * @param {Array<{ title: string, source: string }>} newsItems 
 * @returns {Promise<string>}
 */
export async function generateDailyRecap(apiKey, newsItems) {
  if (!apiKey || apiKey.trim().length === 0 || !Array.isArray(newsItems) || newsItems.length === 0) {
    return '📊 **نشرة FeedPulse الإخبارية اليومية:**\n' +
      newsItems.map((n, i) => `${i + 1}. **${n.title}** (${n.source})`).join('\n');
  }

  try {
    const ai = getAIClient(apiKey);
    const model = ai.getGenerativeModel({ model: 'gemini-1.5-flash' });

    const newsListText = newsItems.map((n, i) => `${i + 1}. ${n.title} [المصدر: ${n.source}]`).join('\n');

    const prompt = `
أنت محرر إخباري. إليك قائمة بأهم الأخبار اليومية:
${newsListText}

قم بصياغة نشرة موجزة بعنوان "⚡ حصاد اليوم من FeedPulse" تلخص أهم الاتجاهات والأحداث في 4 إلى 5 نقاط رئيسية بالعربية بأسلوب إعلامي شيق.
`;

    const result = await model.generateContent(prompt);
    return result.response.text().trim();
  } catch (err) {
    console.warn('Daily recap AI error:', err.message);
    return '📊 **نشرة FeedPulse الإخبارية اليومية:**\n' +
      newsItems.map((n, i) => `🔹 **${n.title}** (${n.source})`).join('\n');
  }
}
