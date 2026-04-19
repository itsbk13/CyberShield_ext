// Gemini API key fetched from backend
const GEMINI_API_KEY = (async () => {
  try {
    const response = await fetch("http://127.0.0.1:8000/cb/get_gemini_key/", {
      method: "GET",
      headers: {
        "Authorization": "Bearer cybershield_extension_token",
        "Content-Type": "application/json"
      }
    });
    if (!response.ok) throw new Error(`Failed: ${response.status}`);
    const data = await response.json();
    return data.key || null;
  } catch (err) {
    console.error("Gemini key fetch error:", err);
    return null;
  }
})();

// Language mapping for Google Translate
const LANGUAGE_MAP = {
  "English": "en",
  "தமிழ் (Tamil)": "ta",
  "తెలుగు (Telugu)": "te",
  "മലയാളം (Malayalam)": "ml",
  "ಕನ್ನಡ (Kannada)": "kn",
  "हिन्दी (Hindi)": "hi",
  "Deutsch": "de",
  "Español": "es",
  "Português": "pt",
  "日本語 (Japanese)": "ja",
  "中文 (Chinese)": "zh",
  "Русский (Russian)": "ru",
  "العربية (Arabic)": "ar",
  "한국어 (Korean)": "ko",
  "ไทย (Thai)": "th"
};

// Initialize variables
let isAnalyseMode = true;
let currentLanguage = "English";
let conversationHistory = [
  {
    role: "system",
    content: "You are CyberShield, a friendly AI scam detector. Respond in a casual, conversational tone like you're chatting with a friend. If I provide a fraud detection result, present it naturally. Otherwise, just chat normally and be helpful!"
  }
];

// Translate text via Google Translate
async function translateText(text, sourceLang, targetLang) {
  try {
    const sourceCode = LANGUAGE_MAP[sourceLang] || "en";
    const targetCode = LANGUAGE_MAP[targetLang] || "en";
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sourceCode}&tl=${targetCode}&dt=t&q=${encodeURIComponent(text)}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Translation failed: ${response.status}`);
    const data = await response.json();
    let translatedText = "";
    for (let i = 0; i < data[0].length; i++) {
      translatedText += data[0][i][0];
    }
    return translatedText || text;
  } catch (err) {
    console.error("Translation error:", err);
    throw err;
  }
}

// Chat with Gemini 2.5 Flash
async function chatWithGemini(messages) {
  const key = await GEMINI_API_KEY;
  if (!key) return "AI service unavailable.";

  try {
    const contents = messages
      .filter(m => m.role !== "system")
      .map(m => ({
        role: m.role === "assistant" ? "model" : "user",
        parts: [{ text: m.content }]
      }));

    const systemMsg = messages.find(m => m.role === "system");

    const requestBody = {
      ...(systemMsg && {
        system_instruction: { parts: [{ text: systemMsg.content }] }
      }),
      contents: contents,
      generationConfig: {
        maxOutputTokens: 200,
        temperature: 0.7
      }
    };

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key=${key}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
      }
    );

    if (!response.ok) {
      const err = await response.text();
      throw new Error(`Gemini error: ${response.status} - ${err}`);
    }

    const data = await response.json();
    return data.candidates[0].content.parts[0].text;

  } catch (err) {
    console.error("Gemini error:", err);
    return "Sorry, I'm having trouble chatting right now!";
  }
}

// Refine fraud detection via Gemini
async function refineFraudDetection(text, modelPrediction) {
  const messages = [
    {
      role: "system",
      content: "You are an AI assistant helping to refine fraud detection accuracy. Given a message and a model prediction, provide a refined assessment of whether the message is phishing, fraud, or safe, and adjust the probability if needed. Respond in the format: 'Refined Prediction: <type> with probability <probability>%'"
    },
    {
      role: "user",
      content: `Message: "${text}"\nModel Prediction: ${modelPrediction.is_phishing ? "Phishing" : modelPrediction.is_fraud ? "Fraud" : "Safe"} with probability ${modelPrediction.probability || 50}%\nRefine this prediction and probability.`
    }
  ];
  return await chatWithGemini(messages);
}

// Rephrase response conversationally
async function redefineResponse(response) {
  const messages = [
    {
      role: "system",
      content: "You are a friendly AI assistant. Rephrase the following response in a casual, conversational tone like you're chatting with a friend."
    },
    {
      role: "user",
      content: `Rephrase this: "${response}"`
    }
  ];
  return await chatWithGemini(messages);
}

// Classify if input needs fraud detection
function needsFraudDetection(text) {
  const lowerText = text.toLowerCase();
  const urlRegex = /(http:\/\/|https:\/\/|\.com)/i;
  const moneyRegex = /(\$|\d+\s*(dollars|usd))/i;
  const suspiciousKeywords = ["urgent", "verify", "account", "login", "password", "click here"];
  return urlRegex.test(lowerText) || moneyRegex.test(lowerText) || suspiciousKeywords.some(kw => lowerText.includes(kw));
}

// Update threat level badge in header
function updateThreatLevel(probability, riskLevel) {
  const threatLevelDiv = document.getElementById("threatLevel");
  let threatClass = "safe";

  if (riskLevel === "CRITICAL") {
    threatClass = "high";
  } else if (riskLevel === "HIGH" || probability >= 67) {
    threatClass = "high";
  } else if (probability >= 34) {
    threatClass = "medium";
  }

  threatLevelDiv.className = `threat-level show ${threatClass}`;
  const label = riskLevel === "CRITICAL" ? "CRITICAL" : threatClass.toUpperCase();
  document.getElementById("threatText").textContent = label;
  document.getElementById("chatContainer").className = `chat-container threat-${threatClass}`;
}

// Render Threat Intelligence Panel with CVE + KEV data
function renderThreatIntelPanel(ti) {
  const panel = document.getElementById("threatIntelPanel");
  const kevBadge = document.getElementById("kevBadge");
  const kevDetails = document.getElementById("kevDetails");
  const cveList = document.getElementById("cveList");
  const analystNote = document.getElementById("analystNote");
  const title = document.getElementById("threatIntelTitle");
  const header = document.getElementById("threatIntelHeader");

  kevBadge.style.display = "none";
  kevDetails.innerHTML = "";
  cveList.innerHTML = "";
  analystNote.innerHTML = "";

  if (!ti || (!ti.kev_matched && (!ti.related_cves || ti.related_cves.length === 0))) {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";

  if (ti.kev_matched) {
    header.style.background = "linear-gradient(90deg, #ff2244, #cc0022)";
    title.textContent = "⚠ THREAT INTELLIGENCE — KEV MATCH";
    kevBadge.style.display = "block";

    const kd = ti.kev_details;
    if (kd) {
      kevDetails.innerHTML = `
        <div class="kev-detail-row"><span class="kev-label">CVE ID</span><span class="kev-value cve-id">${kd.cve_id}</span></div>
        <div class="kev-detail-row"><span class="kev-label">Vendor</span><span class="kev-value">${kd.vendor}</span></div>
        <div class="kev-detail-row"><span class="kev-label">Product</span><span class="kev-value">${kd.product}</span></div>
        <div class="kev-detail-row"><span class="kev-label">Added to KEV</span><span class="kev-value">${kd.date_added}</span></div>
        <div class="kev-detail-row"><span class="kev-label">Description</span><span class="kev-value">${kd.short_description}</span></div>
        <div class="kev-detail-row"><span class="kev-label">Required Action</span><span class="kev-value kev-action">${kd.required_action}</span></div>
      `;
    }
  } else {
    header.style.background = "linear-gradient(90deg, #ff8800, #cc5500)";
    title.textContent = "⚠ THREAT INTELLIGENCE — CVEs FOUND";
  }

  if (ti.related_cves && ti.related_cves.length > 0) {
    const cvesHtml = ti.related_cves.map(cve => `
      <div class="cve-item">
        <span class="cve-id">${cve.id}</span>
        ${cve.cvss_score ? `<span class="cvss-badge cvss-${getCvssClass(cve.cvss_score)}">CVSS ${cve.cvss_score}</span>` : ''}
        <div class="cve-desc">${cve.description}</div>
      </div>
    `).join('');
    cveList.innerHTML = `<div class="cve-section-title">Related CVEs</div>${cvesHtml}`;
  }

  if (ti.analyst_note) {
    analystNote.innerHTML = `<div class="analyst-note-text">🔍 ${ti.analyst_note}</div>`;
  }

  const toggle = document.getElementById("threatIntelToggle");
  const body = document.getElementById("threatIntelBody");
  header.onclick = () => {
    const isOpen = body.style.display !== "none";
    body.style.display = isOpen ? "none" : "block";
    toggle.innerHTML = isOpen ? "&#9650;" : "&#9660;";
  };
}

// CVSS severity class helper
function getCvssClass(score) {
  if (score >= 9.0) return "critical";
  if (score >= 7.0) return "high";
  if (score >= 4.0) return "medium";
  return "low";
}

// Add message to chat with typing animation
async function addMessage(text, type) {
  const messagesDiv = document.getElementById("messages");
  const wrapper = document.createElement("div");
  wrapper.className = `message-wrapper ${type}`;
  const avatar = document.createElement("div");
  avatar.className = `message-avatar ${type}`;
  const content = document.createElement("div");
  content.className = "message-content";
  const message = document.createElement("div");
  message.className = "message";
  const timestamp = document.createElement("div");
  timestamp.className = "message-timestamp";
  timestamp.textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  content.appendChild(message);
  content.appendChild(timestamp);
  wrapper.appendChild(type === "bot" ? avatar : content);
  wrapper.appendChild(type === "bot" ? content : avatar);
  messagesDiv.appendChild(wrapper);

  document.getElementById("welcomeMessage").style.display = "none";

  if (type === "bot") {
    const words = text.split(" ");
    for (let i = 0; i < words.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 100));
      message.textContent += (i === 0 ? "" : " ") + words[i];
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
  } else {
    message.textContent = text;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  avatar.innerHTML = type === "bot"
    ? '<svg class="shield-icon" viewBox="0 0 24 24"><path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,7C13.4,7 14.8,8.6 14.8,10.5V11.5C15.4,11.5 16,12.4 16,13V16C16,16.6 15.6,17 15,17H9C8.4,17 8,16.6 8,16V13C8,12.4 8.4,11.5 9,11.5V10.5C9,8.6 10.6,7 12,7M12,8.2C11.2,8.2 10.2,8.7 10.2,10.5V11.5H13.8V10.5C13.8,8.7 12.8,8.2 12,8.2Z"/></svg>'
    : '<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>';
}

// Main logic
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("input");
  const sendButton = document.getElementById("sendButton");
  const analyseToggle = document.getElementById("analyseToggle");
  const languageSelect = document.getElementById("languageSelect");
  const scanningIndicator = document.getElementById("scanningIndicator");

  languageSelect.addEventListener("change", (e) => {
    currentLanguage = e.target.value;
    addMessage(`Language set to: ${currentLanguage}`, "bot");
  });

  analyseToggle.addEventListener("click", () => {
    isAnalyseMode = !isAnalyseMode;
    analyseToggle.classList.toggle("active", isAnalyseMode);
    analyseToggle.classList.toggle("inactive", !isAnalyseMode);
    addMessage(`Analyse mode ${isAnalyseMode ? "on" : "off"}`, "bot");
  });

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    await addMessage(text, "user");
    input.value = "";

    let textToSend = text;
    if (currentLanguage !== "English") {
      try {
        textToSend = await translateText(text, currentLanguage, "en");
      } catch (err) {
        await addMessage(`Translation failed: ${err.message}`, "bot");
        return;
      }
    }

    conversationHistory.push({ role: "user", content: textToSend });
    const forceFraudDetection = textToSend.startsWith("@");

    if (isAnalyseMode) {
      const textForAnalysis = forceFraudDetection ? textToSend.slice(1).trim() : textToSend;
      scanningIndicator.classList.add("show");

      try {
        const res = await fetch("http://127.0.0.1:8000/cb/analyze_text/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: textForAnalysis })
        });

        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        const data = await res.json();
        console.log("Response from Django:", data);

        const ti = data.threat_intelligence || {};

        let kevContext = "";
        if (ti.kev_matched && ti.kev_details) {
          kevContext = `CRITICAL: KEV MATCH detected. CVE ${ti.kev_details.cve_id} affects ${ti.kev_details.vendor} ${ti.kev_details.product} and is ACTIVELY EXPLOITED in the wild as per CISA KEV list. Required action: ${ti.kev_details.required_action}`;
        } else if (ti.related_cves && ti.related_cves.length > 0) {
          kevContext = `Related CVEs found: ${ti.related_cves.map(c => `${c.id} (CVSS: ${c.cvss_score || 'N/A'})`).join(", ")}. Review and apply patches based on CVSS severity.`;
        }

        const refinedPrediction = await refineFraudDetection(textForAnalysis, data);
        let refinedType = "LOW RISK";
        let refinedProbability = data.probability || 50;
        const predictionMatch = refinedPrediction.match(/Refined Prediction: (\w+) with probability (\d+)%/);
        if (predictionMatch) {
          refinedType = predictionMatch[1].toUpperCase();
          refinedProbability = parseInt(predictionMatch[2]);
        }

        updateThreatLevel(refinedProbability, ti.risk_level);
        renderThreatIntelPanel(ti);

        const result = refinedType.includes("PHISHING") || refinedType.includes("FRAUD")
          ? `🚨 Potential ${refinedType} detected with ${refinedProbability}% probability! ${data.advice || "Be careful!"}${kevContext ? " " + kevContext : ""}`
          : `No immediate threats detected (probability: ${refinedProbability}%). ${data.advice || "Stay safe!"}${kevContext ? " Note: " + kevContext : ""}`;

        conversationHistory.push({ role: "system", content: `Fraud detection result: ${result}` });
        let geminiResponse = await chatWithGemini(conversationHistory);
        geminiResponse = await redefineResponse(geminiResponse);
        await addMessage(geminiResponse, "bot");

        if (currentLanguage !== "English") {
          try {
            const translatedResponse = await translateText(geminiResponse, "en", currentLanguage);
            await addMessage(translatedResponse, "bot");
          } catch (err) {
            await addMessage(`Translation failed: ${err.message}`, "bot");
          }
        }

        conversationHistory.push({ role: "assistant", content: geminiResponse });
      } catch (err) {
        console.error("Fetch error:", err);
        await addMessage(`Fetch failed: ${err.message}`, "bot");
      } finally {
        scanningIndicator.classList.remove("show");
      }
    } else {
      updateThreatLevel(0, "LOW");
      renderThreatIntelPanel(null);

      let geminiResponse = await chatWithGemini(conversationHistory);
      geminiResponse = await redefineResponse(geminiResponse);
      await addMessage(geminiResponse, "bot");

      if (currentLanguage !== "English") {
        try {
          const translatedResponse = await translateText(geminiResponse, "en", currentLanguage);
          await addMessage(translatedResponse, "bot");
        } catch (err) {
          await addMessage(`Translation failed: ${err.message}`, "bot");
        }
      }

      conversationHistory.push({ role: "assistant", content: geminiResponse });
    }
  }

  sendButton.addEventListener("click", sendMessage);
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  input.addEventListener("input", () => {
    sendButton.classList.toggle("active", input.value.trim());
    sendButton.classList.toggle("inactive", !input.value.trim());
  });
});