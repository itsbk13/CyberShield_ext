// Mistral AI API Key (replace with your actual key)
const MISTRAL_API_KEY = "your_mistral_api_key_here";

// Utility function to translate text using Google Translate API
async function translateText(text, sourceLang, targetLang) {
  try {
    const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=${sourceLang}&tl=${targetLang}&dt=t&q=${encodeURIComponent(
      text
    )}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Translation failed: ${response.status}`);
    }
    const data = await response.json();
    console.log("Google Translate API Response:", data);

    // Handle multi-sentence responses by joining all translated parts
    let translatedText = "";
    for (let i = 0; i < data[0].length; i++) {
      translatedText += data[0][i][0]; // Join each translated sentence
    }
    return translatedText || text; // Fallback to original text if translation fails
  } catch (err) {
    console.error("Translation error:", err);
    throw err;
  }
}

// Utility function to call Mistral AI for conversational responses or fraud detection refinement
async function chatWithMistral(messages) {
  try {
    const requestBody = {
      model: "mistral-medium",
      messages: messages,
      max_tokens: 150,
    };

    console.log(
      "Mistral API Request Payload:",
      JSON.stringify(requestBody, null, 2)
    );

    const response = await fetch("https://api.mistral.ai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${MISTRAL_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    const responseText = await response.text();
    console.log("Mistral API Response Status:", response.status);
    console.log("Mistral API Response Body:", responseText);

    if (!response.ok) {
      throw new Error(
        `Mistral AI request failed: ${response.status} - ${responseText}`
      );
    }

    const data = JSON.parse(responseText);
    return data.choices[0].message.content;
  } catch (err) {
    console.error("Detailed Mistral AI error:", err);
    return `Sorry, I'm having trouble chatting right now! Error: ${err.message}`;
  }
}

// Utility function to refine fraud detection accuracy using Mistral AI
async function refineFraudDetection(text, modelPrediction) {
  const messages = [
    {
      role: "system",
      content:
        "You are an AI assistant helping to refine fraud detection accuracy. Given a message and a model prediction, provide a refined assessment of whether the message is phishing, fraud, or safe, and adjust the probability if needed. Respond in the format: 'Refined Prediction: <type> with probability <probability>%'",
    },
    {
      role: "user",
      content: `Message: "${text}"\nModel Prediction: ${
        modelPrediction.is_phishing
          ? "Phishing"
          : modelPrediction.is_fraud
          ? "Fraud"
          : "Safe"
      } with probability ${
        modelPrediction.probability || 50
      }%\nRefine this prediction and probability.`,
    },
  ];

  return await chatWithMistral(messages);
}

// Utility function to redefine (rephrase) a response using Mistral AI
async function redefineResponse(response) {
  const messages = [
    {
      role: "system",
      content:
        "You are a friendly AI assistant. Rephrase the following response in a casual, conversational tone like you're chatting with a friend.",
    },
    {
      role: "user",
      content: `Rephrase this: "${response}"`,
    },
  ];

  return await chatWithMistral(messages);
}

// Function to classify user input (needs fraud detection or conversational)
function needsFraudDetection(text) {
  const lowerText = text.toLowerCase();
  const urlRegex = /(http:\/\/|https:\/\/|\.com)/i;
  const moneyRegex = /(\$|\d+\s*(dollars|usd))/i;
  const suspiciousKeywords = [
    "urgent",
    "verify",
    "account",
    "login",
    "password",
    "click here",
  ];

  return (
    urlRegex.test(lowerText) ||
    moneyRegex.test(lowerText) ||
    suspiciousKeywords.some((keyword) => lowerText.includes(keyword))
  );
}

// Function to update the threat level UI
function updateThreatLevel(alertLevel) {
  const threatLevelDiv = document.getElementById("threatLevel");
  let color = "#2ecc71"; // Default (low risk)

  if (
    alertLevel.toLowerCase().includes("phishing") ||
    alertLevel.toLowerCase().includes("fraud")
  ) {
    color = "#e74c3c"; // High risk
  } else if (alertLevel.toLowerCase().includes("medium")) {
    color = "#f39c12";
  }

  threatLevelDiv.innerText = `Current Threat: ${alertLevel.toUpperCase()}`;
  threatLevelDiv.style.backgroundColor = color;
  threatLevelDiv.style.display = "block"; // Show threat level
}

// Function to add messages to chat with typing animation for bot messages
async function addMessage(text, type) {
  const messagesDiv = document.getElementById("messages");
  const messageDiv = document.createElement("div");

  messageDiv.className = `message ${type}`;
  messagesDiv.appendChild(messageDiv);

  // Hide welcome message after first message
  document.getElementById("welcomeMessage").style.display = "none";

  if (type === "bot") {
    // Split the text into words for typing animation
    const words = text.split(" ");
    messageDiv.innerText = ""; // Start with empty text

    // Display each word with a delay
    for (let i = 0; i < words.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, 100)); // 100ms delay between words
      messageDiv.innerText += (i === 0 ? "" : " ") + words[i];
      messagesDiv.scrollTop = messagesDiv.scrollHeight; // Auto-scroll as words are added
    }
  } else {
    // For user messages, display instantly
    messageDiv.innerText = text;
    messagesDiv.scrollTop = messagesDiv.scrollHeight; // Auto-scroll
  }
}

// Maintain conversation history for Mistral AI
let conversationHistory = [
  {
    role: "system",
    content:
      "You are CyberShield, a friendly AI scam detector. Respond in a casual, conversational tone like you're chatting with a friend. If I provide a fraud detection result, present it naturally. Otherwise, just chat normally and be helpful!",
  },
];

// Function to send message (used by both Send button and Enter key)
async function sendMessage() {
  const input = document.getElementById("input");
  const text = input.value.trim();
  if (!text) {
    await addMessage("Gimme somethin’ to work with, bruh!", "bot");
    return;
  }

  // Add user message to chat (in original language)
  await addMessage(text, "user");

  // Clear the input box immediately after the user sends the message
  document.getElementById("input").value = "";

  // Translate input to English if not already in English
  let textToSend = text;
  if (selectedLang !== "en") {
    try {
      textToSend = await translateText(text, selectedLang, "en");
    } catch (err) {
      await addMessage(`Translation failed: ${err.message}`, "bot");
      return;
    }
  }

  // Add translated user message to conversation history
  conversationHistory.push({ role: "user", content: textToSend });

  // Check if the message starts with '@' or needs fraud detection
  const forceFraudDetection = textToSend.startsWith("@");
  const heuristicFraudDetection = needsFraudDetection(textToSend);

  if (forceFraudDetection || heuristicFraudDetection) {
    // If the message starts with '@', remove the prefix for analysis
    const textForAnalysis = forceFraudDetection
      ? textToSend.slice(1).trim()
      : textToSend;

    // Call Django backend for fraud detection
    const body = JSON.stringify({ text: textForAnalysis });
    console.log("Sending request with body:", body);

    try {
      const res = await fetch("http://127.0.0.1:8000/cb/analyze/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
      });

      if (!res.ok) {
        throw new Error(`HTTP error! Status: ${res.status}`);
      }

      const data = await res.json();
      console.log("Response from Django:", data);

      // Use Mistral AI to refine the fraud detection accuracy
      const refinedPrediction = await refineFraudDetection(textForAnalysis, {
        is_phishing: data.is_phishing,
        is_fraud: data.is_fraud,
        probability: data.probability || 50, // Fallback probability if not provided
      });

      // Parse the refined prediction from Mistral AI
      let refinedType = "LOW RISK";
      let refinedProbability = 50;
      const predictionMatch = refinedPrediction.match(
        /Refined Prediction: (\w+) with probability (\d+)%/
      );
      if (predictionMatch) {
        refinedType = predictionMatch[1].toUpperCase();
        refinedProbability = parseInt(predictionMatch[2]);
      }

      // Update threat level UI based on refined prediction
      const alertType = refinedType.includes("PHISHING")
        ? "PHISHING"
        : refinedType.includes("FRAUD")
        ? "FRAUD"
        : "LOW RISK";
      updateThreatLevel(alertType);

      // Prepare fraud detection result
      const result =
        refinedType.includes("PHISHING") || refinedType.includes("FRAUD")
          ? `🚨 Potential ${alertType} detected with ${refinedProbability}% probability! Be very careful with this message.`
          : `No immediate threats detected (probability: ${refinedProbability}%). Stay vigilant!`;

      // Add the fraud detection result to the conversation history
      conversationHistory.push({
        role: "system",
        content: `Fraud detection result: ${result}`,
      });

      // Use Mistral AI to present the result conversationally
      let mistralResponse = await chatWithMistral(conversationHistory);

      // Redefine the Mistral response to sound more natural
      mistralResponse = await redefineResponse(mistralResponse);

      // Add the English response to the chat with typing animation
      await addMessage(mistralResponse, "bot");

      // If selected language is not English, translate the response back
      if (selectedLang !== "en") {
        try {
          const translatedResponse = await translateText(
            mistralResponse,
            "en",
            selectedLang
          );
          await addMessage(translatedResponse, "bot");
        } catch (err) {
          await addMessage(`Translation failed: ${err.message}`, "bot");
        }
      }

      // Add Mistral's response to conversation history
      conversationHistory.push({ role: "assistant", content: mistralResponse });
    } catch (err) {
      console.error("Fetch error:", err);
      await addMessage(`Fetch failed: ${err.message}`, "bot");
    }
  } else {
    // Conversational query—use Mistral AI directly
    let mistralResponse = await chatWithMistral(conversationHistory);

    // Redefine the Mistral response to sound more natural
    mistralResponse = await redefineResponse(mistralResponse);

    // Add the English response to the chat with typing animation
    await addMessage(mistralResponse, "bot");

    // If selected language is not English, translate the response back
    if (selectedLang !== "en") {
      try {
        const translatedResponse = await translateText(
          mistralResponse,
          "en",
          selectedLang
        );
        await addMessage(translatedResponse, "bot");
      } catch (err) {
        await addMessage(`Translation failed: ${err.message}`, "bot");
      }
    }

    // Add Mistral's response to conversation history
    conversationHistory.push({ role: "assistant", content: mistralResponse });
  }
}

// Main logic
let selectedLang = "en"; // Default to English

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("input");
  const sendButton = document.getElementById("sendButton");
  const dropdownSelected = document.getElementById("dropdownSelected");
  const dropdownOptions = document.getElementById("dropdownOptions");

  // Toggle dropdown on click
  dropdownSelected.addEventListener("click", () => {
    dropdownOptions.classList.toggle("show");
  });

  // Handle option selection
  dropdownOptions.addEventListener("click", (event) => {
    const target = event.target;
    if (target.classList.contains("dropdown-option")) {
      selectedLang = target.getAttribute("data-value");
      dropdownSelected.textContent = target.textContent;
      dropdownOptions.classList.remove("show");
      addMessage(`Language set to: ${target.textContent}`, "bot");
    }
  });

  // Close dropdown if clicking outside
  document.addEventListener("click", (event) => {
    if (
      !dropdownSelected.contains(event.target) &&
      !dropdownOptions.contains(event.target)
    ) {
      dropdownOptions.classList.remove("show");
    }
  });

  // Send button click
  sendButton.addEventListener("click", sendMessage);

  // Enable "Enter" key to send message
  input.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      sendMessage();
    }
  });
});
