// Mistral AI API Key (replace with your actual key)
const MISTRAL_API_KEY = "fu7Iba5duoUzdBDT5MBXn8bhvuVkxbqc";

// Language mapping for Google Translate
const LANGUAGE_MAP = {
  "English": "en",
  "Español": "es",
  "Français": "fr",
  "Deutsch": "de",
  "Italiano": "it",
  "Português": "pt",
  "日本語 (Japanese)": "ja",
  "中文 (Chinese)": "zh",
  "Русский (Russian)": "ru",
  "العربية (Arabic)": "ar",
  "हिन्दी (Hindi)": "hi",
  "한국어 (Korean)": "ko",
  "Türkçe": "tr",
  "Nederlands": "nl",
  "Svenska": "sv",
  "Polski": "pl",
  "ไทย (Thai)": "th"
};

// Initialize variables
let isAnalyseMode = true;
let currentLanguage = "English";
let isTyping = false;
let conversationHistory = [
  {
    role: "system",
    content: "You are CyberShield, a friendly AI scam detector. Respond in a casual, conversational tone like you're chatting with a friend. If I provide a fraud detection result, present it naturally. Otherwise, just chat normally and be helpful!"
  }
];

// Utility function to translate text using Google Translate API
async function translateText(text, sourceLang, targetLang) {
  try {
    const sourceCode = LANGUAGE_MAP[sourceLang] || "en";
    const targetCode = LANGUAGE_MAP[targetLang] || "en";
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sourceCode}&tl=${targetCode}&dt=t&q=${encodeURIComponent(text)}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Translation failed: ${response.status}`);
    }
    const data = await response.json();
    console.log("Google Translate API Response:", data);

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

// Utility function to call Mistral AI
async function chatWithMistral(messages) {
  try {
    const requestBody = { model: "mistral-medium", messages, max_tokens: 150 };
    console.log("Mistral API Request Payload:", JSON.stringify(requestBody, null, 2));
    const response = await fetch("https://api.mistral.ai/v1/chat/completions", {
      method: "POST",
      headers: { Authorization: `Bearer ${MISTRAL_API_KEY}`, "Content-Type": "application/json" },
      body: JSON.stringify(requestBody)
    });
    const responseText = await response.text();
    console.log("Mistral API Response Status:", response.status);
    console.log("Mistral API Response Body:", responseText);

    if (!response.ok) {
      throw new Error(`Mistral AI request failed: ${response.status} - ${responseText}`);
    }
    const data = JSON.parse(responseText);
    return data.choices[0].message.content;
  } catch (err) {
    console.error("Detailed Mistral AI error:", err);
    return "Sorry, I'm having trouble chatting right now!";
  }
}

// Utility function to refine fraud detection
async function refineFraudDetection(text, modelPrediction) {
  const messages = [
    { role: "system", content: "You are an AI assistant helping to refine fraud detection accuracy. Given a message and a model prediction, provide a refined assessment of whether the message is phishing, fraud, or safe, and adjust the probability if needed. Respond in the format: 'Refined Prediction: <type> with probability <probability>%'" },
    { role: "user", content: `Message: "${text}"\nModel Prediction: ${modelPrediction.is_phishing ? "Phishing" : modelPrediction.is_fraud ? "Fraud" : "Safe"} with probability ${modelPrediction.probability || 50}%\nRefine this prediction and probability.` }
  ];
  return await chatWithMistral(messages);
}

// Utility function to redefine response
async function redefineResponse(response) {
  const messages = [
    { role: "system", content: "You are a friendly AI assistant. Rephrase the following response in a casual, conversational tone like you're chatting with a friend." },
    { role: "user", content: `Rephrase this: "${response}"` }
  ];
  return await chatWithMistral(messages);
}

// Function to classify user input
function needsFraudDetection(text) {
  const lowerText = text.toLowerCase();
  const urlRegex = /(http:\/\/|https:\/\/|\.com)/i;
  const moneyRegex = /(\$|\d+\s*(dollars|usd))/i;
  const suspiciousKeywords = ["urgent", "verify", "account", "login", "password", "click here"];
  return urlRegex.test(lowerText) || moneyRegex.test(lowerText) || suspiciousKeywords.some(keyword => lowerText.includes(keyword));
}

// Function to update threat level UI
function updateThreatLevel(probability) {
  const threatLevelDiv = document.getElementById("threatLevel");
  let threatClass = "safe";
  if (probability >= 67) threatClass = "high";
  else if (probability >= 34) threatClass = "medium";
  threatLevelDiv.className = `threat-level show ${threatClass}`;
  document.getElementById("threatText").textContent = threatClass.toUpperCase();
  document.getElementById("chatContainer").className = `chat-container threat-${threatClass}`;
}

// Function to add messages with typing animation
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
  avatar.innerHTML = type === "bot" ? '<svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/></svg>' : '<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>';
}

// Main logic
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("input");
  const sendButton = document.getElementById("sendButton");
  const analyseToggle = document.getElementById("analyseToggle");
  const languageSelect = document.getElementById("languageSelect");
  const scanningIndicator = document.getElementById("scanningIndicator");

  // Update current language
  languageSelect.addEventListener("change", (e) => {
    currentLanguage = e.target.value;
    addMessage(`Language set to: ${currentLanguage}`, "bot");
  });

  // Toggle analyse mode
  analyseToggle.addEventListener("click", () => {
    isAnalyseMode = !isAnalyseMode;
    analyseToggle.classList.toggle("active", isAnalyseMode);
    analyseToggle.classList.toggle("inactive", !isAnalyseMode);
    addMessage(`Analyse mode ${isAnalyseMode ? "on" : "off"}`, "bot");
  });

  // Send message
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
    const heuristicFraudDetection = needsFraudDetection(textToSend);

    if ((forceFraudDetection || heuristicFraudDetection) && isAnalyseMode) {
      const textForAnalysis = forceFraudDetection ? textToSend.slice(1).trim() : textToSend;
      scanningIndicator.classList.add("show");

      try {
        const res = await fetch("http://127.0.0.1:8000/cb/analyze/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: textForAnalysis })
        });

        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        const data = await res.json();
        console.log("Response from Django:", data);

        const refinedPrediction = await refineFraudDetection(textForAnalysis, data);
        let refinedType = "LOW RISK";
        let refinedProbability = data.probability || 50;
        const predictionMatch = refinedPrediction.match(/Refined Prediction: (\w+) with probability (\d+)%/);
        if (predictionMatch) {
          refinedType = predictionMatch[1].toUpperCase();
          refinedProbability = parseInt(predictionMatch[2]);
        }

        updateThreatLevel(refinedProbability);
        const result = refinedType.includes("PHISHING") || refinedType.includes("FRAUD")
          ? `🚨 Potential ${refinedType} detected with ${refinedProbability}% probability! ${data.advice || "Be careful!"}`
          : `No immediate threats detected (probability: ${refinedProbability}%). ${data.advice || "Stay safe!"}`;

        conversationHistory.push({ role: "system", content: `Fraud detection result: ${result}` });
        let mistralResponse = await chatWithMistral(conversationHistory);
        mistralResponse = await redefineResponse(mistralResponse);
        await addMessage(mistralResponse, "bot");

        if (currentLanguage !== "English") {
          try {
            const translatedResponse = await translateText(mistralResponse, "en", currentLanguage);
            await addMessage(translatedResponse, "bot");
          } catch (err) {
            await addMessage(`Translation failed: ${err.message}`, "bot");
          }
        }

        conversationHistory.push({ role: "assistant", content: mistralResponse });
      } catch (err) {
        console.error("Fetch error:", err);
        await addMessage(`Fetch failed: ${err.message}`, "bot");
      } finally {
        scanningIndicator.classList.remove("show");
      }
    } else {
      updateThreatLevel(0);
      let mistralResponse = await chatWithMistral(conversationHistory);
      mistralResponse = await redefineResponse(mistralResponse);
      await addMessage(mistralResponse, "bot");

      if (currentLanguage !== "English") {
        try {
          const translatedResponse = await translateText(mistralResponse, "en", currentLanguage);
          await addMessage(translatedResponse, "bot");
        } catch (err) {
          await addMessage(`Translation failed: ${err.message}`, "bot");
        }
      }

      conversationHistory.push({ role: "assistant", content: mistralResponse });
    }
  }

  // Event listeners
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