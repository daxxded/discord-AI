// file: renderer.js
const assistantBar = document.getElementById('assistantBar');
const sendButton = document.getElementById('sendButton');
const menuButton = document.getElementById('menuButton');
const settingsMenu = document.getElementById('settingsMenu');
const responseArea = document.getElementById('responseArea');
const modelOptions = document.getElementById('modelOptions');
const simulateVoiceButton = document.getElementById('simulateVoice');
const visualizer = document.querySelector('.left-visualizer');

let configCache = null;
let activeModel = null;
let isUserSpeaking = false;
let isAssistantSpeaking = false;

const THEME_KEY = 'hyperplexity-theme';
const MODEL_KEY = 'hyperplexity-model';

async function loadConfig() {
  if (!configCache) {
    configCache = await window.hyperplexity.readConfig();
  }
  return configCache;
}

function applyTheme(theme) {
  document.body.classList.remove('theme-light', 'theme-dark', 'theme-night');
  document.body.classList.add(`theme-${theme}`);
  localStorage.setItem(THEME_KEY, theme);

  document.querySelectorAll('.theme-buttons button').forEach((button) => {
    button.classList.toggle('active', button.dataset.theme === theme);
  });
}

function setUserSpeaking(active) {
  isUserSpeaking = active;
  assistantBar.classList.toggle('user-speaking', isUserSpeaking);
}

function setAssistantSpeaking(active) {
  isAssistantSpeaking = active;
  visualizer.classList.toggle('speaking', isAssistantSpeaking);
}

function showResponse(text) {
  responseArea.textContent = text;
}

function buildModelOptions(models, selectedModel) {
  modelOptions.innerHTML = '';
  models.forEach((model) => {
    const label = document.createElement('label');
    const input = document.createElement('input');
    input.type = 'radio';
    input.name = 'model';
    input.value = model.id;
    input.checked = model.id === selectedModel;
    input.addEventListener('change', () => {
      activeModel = model.id;
      localStorage.setItem(MODEL_KEY, activeModel);
    });

    label.appendChild(input);
    label.append(` ${model.label}`);
    modelOptions.appendChild(label);
  });
}

function toggleSettingsMenu() {
  settingsMenu.classList.toggle('hidden');
}

function speakText(text) {
  if (!window.speechSynthesis) {
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'it-IT';
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  utterance.onstart = () => {
    setAssistantSpeaking(true);
  };

  utterance.onend = () => {
    setAssistantSpeaking(false);
  };

  window.speechSynthesis.speak(utterance);
}

function buildSystemPrompt(basePrompt) {
  return `${basePrompt}\n\nRegole JSON obbligatorie:\n- Rispondi sempre e solo con JSON valido.\n- Per risposte informative usa type: \"answer_only\" con arguments.text.\n- Per aprire siti usa type: \"open_url\" con arguments.url.\n- Per aprire cartelle usa type: \"open_folder\" con arguments.path.\n- Non aggiungere testo fuori dal JSON.`;
}

async function askAssistant(userText) {
  const config = await loadConfig();
  const apiKey = config.apiKey;

  if (!apiKey || apiKey.includes('INSERISCI')) {
    showResponse('Inserisci la tua API key in config.json.');
    return;
  }

  const modelId = activeModel || config.defaultModel;
  const systemPrompt = buildSystemPrompt(config.systemPrompt);

  setAssistantSpeaking(true);

  const payload = {
    model: modelId,
    max_tokens: 600,
    system: systemPrompt,
    messages: [
      {
        role: 'user',
        content: userText
      }
    ]
  };

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    const assistantText = data?.content?.[0]?.text || '';

    let parsed;
    try {
      parsed = JSON.parse(assistantText);
    } catch (error) {
      showResponse('Risposta non valida ricevuta dal modello.');
      setAssistantSpeaking(false);
      return;
    }

    if (parsed.type === 'answer_only') {
      const answer = parsed.arguments?.text || 'Nessuna risposta.';
      showResponse(answer);
      speakText(answer);
      return;
    }

    if (parsed.type === 'open_url' || parsed.type === 'open_folder') {
      await window.hyperplexity.performAction(parsed);
      const spokenText = parsed.type === 'open_url'
        ? 'Ok, apro il sito richiesto.'
        : 'Ok, apro la cartella richiesta.';
      showResponse(spokenText);
      speakText(spokenText);
      return;
    }

    showResponse('Tipo di azione non riconosciuto.');
  } catch (error) {
    showResponse('Errore durante la chiamata API.');
  } finally {
    setAssistantSpeaking(false);
  }
}

async function requestMicrophone() {
  try {
    await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error) {
    showResponse('Permesso microfono negato o non disponibile.');
  }
}

sendButton.addEventListener('click', async () => {
  const userText = window.prompt('Cosa hai detto?');
  if (userText && userText.trim()) {
    await askAssistant(userText.trim());
  }
});

menuButton.addEventListener('click', toggleSettingsMenu);

simulateVoiceButton.addEventListener('click', () => {
  setUserSpeaking(!isUserSpeaking);
});

document.querySelectorAll('.theme-buttons button').forEach((button) => {
  button.addEventListener('click', () => {
    const theme = button.getAttribute('data-theme');
    applyTheme(theme);
  });
});

window.addEventListener('click', (event) => {
  if (!settingsMenu.contains(event.target) && event.target !== menuButton) {
    settingsMenu.classList.add('hidden');
  }
});

(async function init() {
  await requestMicrophone();

  const config = await loadConfig();
  const savedTheme = localStorage.getItem(THEME_KEY) || 'dark';
  const savedModel = localStorage.getItem(MODEL_KEY) || config.defaultModel;

  activeModel = savedModel;
  buildModelOptions(config.models, activeModel);
  applyTheme(savedTheme);
})();
