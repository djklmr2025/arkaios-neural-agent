const path = require('path');
const constants = {
  ACCESS_TOKEN_STORE_KEY: '_NA_ACCESS_TOK',
  REFRESH_TOKEN_STORE_KEY: '_NA_REFRESH_TOK',
  DEVICE_ID_STORE_KEY: '_NA_DEVICE_ID',
  LAST_BACKGROUND_MODE_VALUE: '_NA_LAST_BACKGROUND_MODE_VALUE',
  LAST_THINKING_MODE_VALUE: '_NA_LAST_THINKING_MODE_VALUE',
};
const { spawn, exec, execSync } = require('child_process');
const crypto = require('crypto');
const express = require('express');
const kill = require('tree-kill');
const http = require('http');
const { v4: uuidv4 } = require('uuid');

const fs = require('fs');
const os = require('os');
const { randomBytes } = crypto;

const electron = require('electron');
const { app, BrowserWindow, Menu, ipcMain, dialog, screen } = electron;
const earlyLogDir = path.join(os.homedir(), "AppData", "Local", "NeuralAgent");
if (!fs.existsSync(earlyLogDir)) fs.mkdirSync(earlyLogDir, { recursive: true });
const earlyLogPath = path.join(earlyLogDir, "main-process.log");
function logMainProcess(message) {
  try {
    fs.appendFileSync(earlyLogPath, `[${new Date().toISOString()}] ${message}\n`, "utf8");
  } catch {}
}
logMainProcess(`boot electronKeys=${Object.keys(electron || {}).join(",")} app=${!!app}`);
process.on("uncaughtException", (err) => {
  logMainProcess(`uncaughtException ${err?.stack || err}`);
});
process.on("unhandledRejection", (err) => {
  logMainProcess(`unhandledRejection ${err?.stack || err}`);
});
const isDev = !app.isPackaged;

function base64URLEncode(str) {
  return str.toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

function sha256(buffer) {
  return crypto.createHash('sha256').update(buffer).digest();
}

function generatePKCE() {
  const codeVerifier = base64URLEncode(crypto.randomBytes(32));
  const codeChallenge = base64URLEncode(sha256(Buffer.from(codeVerifier)));
  return { codeVerifier, codeChallenge };
}

async function loadWslSetup() {
  return import('./electron/utils/wslSetup.mjs');
}

class LocalJsonStore {
  constructor() {
    const appDataDir = path.join(os.homedir(), "AppData", "Local", "NeuralAgent");
    if (!fs.existsSync(appDataDir)) fs.mkdirSync(appDataDir, { recursive: true });
    this.filePath = path.join(appDataDir, "electron-store.json");
    this.data = {};
    try {
      if (fs.existsSync(this.filePath)) {
        this.data = JSON.parse(fs.readFileSync(this.filePath, "utf8"));
      }
    } catch (err) {
      console.error("Failed to load local store:", err);
      this.data = {};
    }
  }

  get(key) {
    return this.data[key];
  }

  set(key, value) {
    this.data[key] = value;
    this.flush();
  }

  delete(key) {
    delete this.data[key];
    this.flush();
  }

  flush() {
    fs.writeFileSync(this.filePath, JSON.stringify(this.data, null, 2), "utf8");
  }
}

const store = new LocalJsonStore();

let mainWindow;
let overlayWindow;
let aiagentProcess;
let backgroundAuthWindow;
let bgAuthProcess;
let bgAgentWindow;
let bgSetupWindow;
let readyToClose = false;
let cerebroProcess;
let frontendServer;
let frontendBaseUrl;

const AGENT_CONFIG_NAMES = ['CLASSIFIER', 'TITLE', 'SUGGESTOR', 'PLANNER', 'COMPUTER_USE'];

function getApiKeysEnvPath() {
  const appDataDir = path.join(os.homedir(), "AppData", "Local", "NeuralAgent");
  if (!fs.existsSync(appDataDir)) fs.mkdirSync(appDataDir, { recursive: true });
  return path.join(appDataDir, "API_KEYS.env");
}

function upsertEnvValue(content, key, value) {
  const safeValue = String(value ?? '').replace(/[\r\n]/g, '').trim();
  const line = `${key}=${safeValue}`;
  const regex = new RegExp(`^${key}=.*$`, 'm');
  if (regex.test(content)) {
    return content.replace(regex, line);
  }
  return `${content.replace(/\s*$/, '')}\n${line}\n`;
}

function ensureLocalDefaults(content) {
  let next = content || '';
  if (!/^JWT_SECRET=/m.test(next)) {
    next = upsertEnvValue(next, 'JWT_SECRET', randomBytes(32).toString('hex'));
  }
  if (!/^JWT_ISS=/m.test(next)) {
    next = upsertEnvValue(next, 'JWT_ISS', 'NeuralAgent_Local');
  }
  return next;
}

function writeAiProviderConfig({ provider = 'google', credential = '', modelId = '' }) {
  const envPath = getApiKeysEnvPath();
  let content = fs.existsSync(envPath) ? fs.readFileSync(envPath, 'utf8') : '';
  content = ensureLocalDefaults(content);

  const normalizedProvider = provider === 'puter' ? 'puter' : 'google';
  const defaultModelId = normalizedProvider === 'puter' ? 'gpt-5-nano' : 'gemini-2.5-flash';
  const selectedModelId = modelId || defaultModelId;

  content = upsertEnvValue(content, 'DEFAULT_AGENT_MODEL_TYPE', normalizedProvider);
  content = upsertEnvValue(content, 'DEFAULT_AGENT_MODEL_ID', selectedModelId);

  for (const agentName of AGENT_CONFIG_NAMES) {
    content = upsertEnvValue(content, `${agentName}_AGENT_MODEL_TYPE`, normalizedProvider);
    content = upsertEnvValue(content, `${agentName}_AGENT_MODEL_ID`, selectedModelId);
  }

  if (normalizedProvider === 'puter') {
    content = upsertEnvValue(content, 'PUTER_AUTH_TOKEN', credential);
    content = upsertEnvValue(content, 'PUTER_OPENAI_BASE_URL', 'https://api.puter.com/puterai/openai/v1/');
    content = upsertEnvValue(content, 'PUTER_TIMEOUT', '30');
    content = upsertEnvValue(content, 'PUTER_MAX_RETRIES', '2');
  } else {
    content = upsertEnvValue(content, 'GEMINI_API_KEY', credential);
    content = upsertEnvValue(content, 'GEMINI_TIMEOUT', '20');
    content = upsertEnvValue(content, 'GEMINI_MAX_RETRIES', '1');
  }

  fs.writeFileSync(envPath, content, 'utf8');
}

function ensureDeviceId() {
  let deviceId = store.get(constants.DEVICE_ID_STORE_KEY);
  if (!deviceId) {
    deviceId = uuidv4();
    store.set(constants.DEVICE_ID_STORE_KEY, deviceId);
    console.log(`[Device ID created]: ${deviceId}`);
  } else {
    console.log(`[Device ID exists]: ${deviceId}`);
  }
}

function getFrontendBuildDir() {
  return path.join(__dirname, 'neuralagent-app', 'build');
}

function startFrontendServer() {
  if (isDev || frontendBaseUrl) {
    return Promise.resolve(frontendBaseUrl);
  }

  return new Promise((resolve, reject) => {
    const buildDir = getFrontendBuildDir();
    const indexPath = path.join(buildDir, 'index.html');

    if (!fs.existsSync(indexPath)) {
      reject(new Error(`Frontend build not found at ${indexPath}`));
      return;
    }

    const frontendApp = express();
    frontendApp.use(express.static(buildDir));
    frontendApp.use((req, res) => {
      res.sendFile(indexPath);
    });

    frontendServer = frontendApp.listen(0, '127.0.0.1', () => {
      const { port } = frontendServer.address();
      frontendBaseUrl = `http://127.0.0.1:${port}`;
      logMainProcess(`frontend server listening ${frontendBaseUrl}`);
      resolve(frontendBaseUrl);
    });

    frontendServer.on('error', reject);
  });
}

function getFrontendUrl(hashPath = '') {
  const normalizedHash = hashPath ? `#${hashPath.startsWith('/') ? hashPath : `/${hashPath}`}` : '';
  const baseUrl = isDev ? 'http://localhost:6763' : frontendBaseUrl;
  if (!baseUrl) {
    throw new Error('Frontend server is not ready');
  }
  return `${baseUrl}/${normalizedHash}`;
}


ipcMain.handle('set-token', (_, token) => {
  store.set(constants.ACCESS_TOKEN_STORE_KEY, token);
  if (!overlayWindow) {
    createOverlayWindow();
  }
  return true;
});

ipcMain.handle('get-token', () => store.get(constants.ACCESS_TOKEN_STORE_KEY));
ipcMain.handle('delete-token', () => {
  store.delete(constants.ACCESS_TOKEN_STORE_KEY);
  if (overlayWindow) {
    overlayWindow.close();
  }
  return true;
});
ipcMain.handle('set-refresh-token', (_, token) => {
  store.set(constants.REFRESH_TOKEN_STORE_KEY, token);
  return true;
});
ipcMain.handle('get-refresh-token', () => store.get(constants.REFRESH_TOKEN_STORE_KEY));
ipcMain.handle('delete-refresh-token', () => {
  store.delete(constants.REFRESH_TOKEN_STORE_KEY);
  return true;
});

ipcMain.handle('get-api-key-status', () => {
  try {
    const envPath = getApiKeysEnvPath();
    if (!fs.existsSync(envPath)) return false;
    const content = fs.readFileSync(envPath, 'utf8');
    const providerMatch = content.match(/^DEFAULT_AGENT_MODEL_TYPE=(.*)$/m);
    const provider = providerMatch?.[1]?.trim() || 'google';
    const keyName = provider === 'puter' ? 'PUTER_AUTH_TOKEN' : 'GEMINI_API_KEY';
    const match = content.match(new RegExp(`^${keyName}=(.*)$`, 'm'));
    if (match && match[1].trim().length > 10) {
      return true;
    }
  } catch (e) {
    console.error(e);
  }
  return false;
});

ipcMain.handle('save-api-key', (_, newKey) => {
  try {
    writeAiProviderConfig({ provider: 'google', credential: newKey, modelId: 'gemini-2.5-flash' });
    startCerebro();
    return true;
  } catch (e) {
    console.error(e);
    return false;
  }
});

ipcMain.handle('save-ai-provider-config', (_, config) => {
  try {
    writeAiProviderConfig(config || {});
    startCerebro();
    return true;
  } catch (e) {
    console.error(e);
    return false;
  }
});

ipcMain.on('expand-overlay', (_, hasSuggestions) => {
  console.log("[Main Process] Received 'expand-overlay' IPC message.");
  expandMinimizeOverlay(true, hasSuggestions);
});

ipcMain.handle('get-last-background-mode-value', () => store.get(constants.LAST_BACKGROUND_MODE_VALUE));
ipcMain.handle('get-last-thinking-mode-value', () => store.get(constants.LAST_THINKING_MODE_VALUE));
ipcMain.on('set-last-thinking-mode-value', (_, lastThinkingModeValue) => store.set(constants.LAST_THINKING_MODE_VALUE, lastThinkingModeValue));

// Handle MINIMIZE request
ipcMain.on('minimize-overlay', () => {
  console.log("[Main Process] Received 'minimize-overlay' IPC message.");
  expandMinimizeOverlay(false);
});

ipcMain.handle('check-background-ready', async () => {
  const { isBackgroundModeReady } = await loadWslSetup();
  return isBackgroundModeReady();
});

ipcMain.handle('start-background-setup', async () => {
  // Prevent duplicate windows
  if (bgSetupWindow && !bgSetupWindow.isDestroyed()) {
    bgSetupWindow.focus();
    return;
  }

  bgSetupWindow = new BrowserWindow({
    width: 600,
    height: 300,
    title: 'Setting up Background Mode',
    resizable: false,
    modal: true,
    icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'electron', 'preload.js'),
      contextIsolation: true,
    },
  });

  bgSetupWindow.loadURL(getFrontendUrl('/background-setup'));

  bgSetupWindow.on('closed', () => {
    bgSetupWindow = null;
  });

  const defaultErr = 'Setup Failed: Please ensure you have Windows 10 or higher and that virtualization is enabled in BIOS.';

  let result = { success: false, error: defaultErr };

  try {
    const { setupBackgroundMode } = await loadWslSetup();
    result = await setupBackgroundMode({
      onStatus: (msg) => {
        if (!bgSetupWindow?.isDestroyed()) {
          bgSetupWindow.webContents.send('setup-status', msg);
        }
      },
      onProgress: (pct) => {
        if (!bgSetupWindow?.isDestroyed()) {
          bgSetupWindow.webContents.send('setup-progress', pct);
        }
      },
    });
  } catch (err) {
    console.error('âŒ Setup failed:', err);
    result = {
      success: false,
      error: err?.message || defaultErr,
    };
  }

  if (bgSetupWindow && !bgSetupWindow.isDestroyed()) {
    bgSetupWindow.webContents.send('setup-complete', result);
  }

  if (result.success) {
    launchBackgroundAuthWindow();
  }

  return result;
});


ipcMain.handle('get-suggestions', async (_, baseURL) => {
  const isWindows = process.platform === 'win32';
  return new Promise((resolve, reject) => {
    let suggestor;
    let settled = false;
    const suggestorEnv = {
      ...process.env,
      NEURALAGENT_USER_ACCESS_TOKEN: store.get(constants.ACCESS_TOKEN_STORE_KEY)
    };

    const finish = (payload) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      resolve(payload);
    };

    const timeout = setTimeout(() => {
      console.error('Suggestor timed out.');
      try {
        if (suggestor && !suggestor.killed) {
          kill(suggestor.pid, 'SIGKILL', () => {});
        }
      } catch (err) {
        console.error('Failed to kill timed out suggestor:', err);
      }
      finish({ suggestions: [], error: 'timeout' });
    }, 60000);

    if (isDev) {
      const pythonPath = isWindows 
        ? path.join(__dirname, 'aiagent', 'venv', 'Scripts', 'python.exe')
        : path.join(__dirname, 'aiagent', 'venv', 'bin', 'python');
      
      const scriptPath = path.join(__dirname, 'aiagent', 'suggestor.py');
      suggestor = spawn(pythonPath, [scriptPath, baseURL], { env: suggestorEnv });
    } else {
      const execPath = isWindows
        ? path.join(process.resourcesPath, 'suggestor.exe')
        : path.join(process.resourcesPath, 'suggestor');
        
      suggestor = spawn(execPath, [baseURL], { env: suggestorEnv });
    }

    let suggestorData = '';

    suggestor.stdout.on('data', (data) => {
      suggestorData += data.toString();
    });

    suggestor.stderr.on('data', (data) => {
      console.error(`Suggestor error: ${data}`);
    });

    suggestor.on('error', (err) => {
      console.error('Failed to start suggestor:', err);
      finish({ suggestions: [], error: err.message });
    });

    suggestor.on('close', (code) => {
      if (settled) return;
      if (code === 0 && suggestorData.trim() !== '') {
        try {
          const suggestions = JSON.parse(suggestorData);
          finish(suggestions);
        } catch (e) {
          console.error('Failed to parse suggestions JSON:', e);
          finish({ suggestions: [], error: 'invalid_json' });
        }
      } else {
        console.error(`Suggestor exited with code ${code} and data:`, suggestorData);
        finish({ suggestions: [], error: `exit_${code}` });
      }
    });
  });
});

ipcMain.on('launch-ai-agent', async (_, baseURL, threadId, backgroundMode) => {
  const isWindows = process.platform === 'win32';
  const isMac = process.platform === 'darwin';

  store.set(constants.LAST_BACKGROUND_MODE_VALUE, backgroundMode.toString());

  if (!backgroundMode) {
    let aiagentSpawnArgs = [];
    let aiagentSpawnCmd = '';

    if (isDev) {
      aiagentSpawnCmd = isWindows 
        ? path.join(__dirname, 'aiagent', 'venv', 'Scripts', 'python.exe')
        : path.join(__dirname, 'aiagent', 'venv', 'bin', 'python');
      aiagentSpawnArgs = [path.join(__dirname, 'aiagent', 'main.py')];
    } else {
      aiagentSpawnCmd = isWindows
        ? path.join(process.resourcesPath, 'agent.exe')
        : path.join(process.resourcesPath, 'agent');
    }

    aiagentProcess = spawn(aiagentSpawnCmd, aiagentSpawnArgs, {
      env: {
        ...process.env,
        NEURALAGENT_API_URL: baseURL,
        NEURALAGENT_THREAD_ID: threadId,
        NEURALAGENT_USER_ACCESS_TOKEN: store.get(constants.ACCESS_TOKEN_STORE_KEY),
        PYTHONUTF8: '1',
      },
    });
    mainWindow?.minimize();
  } else {
    // VERY IMPORTANT
    const envVars = {
      NEURALAGENT_API_URL: baseURL, // 'http://192.168.8.101:8000',
      NEURALAGENT_THREAD_ID: threadId,
      NEURALAGENT_USER_ACCESS_TOKEN: store.get(constants.ACCESS_TOKEN_STORE_KEY),
      SKIP_LLM_API_KEY_VERIFICATION: 'true',
      PYTHONUTF8: '1',
    };

    const shellCommand = Object.entries(envVars)
      .map(([k, v]) => `${k}="${v}"`).join(' ') + ' bash /agent/launch_bg_agent.sh';

    aiagentProcess = spawn('wsl', ['-d', 'NeuralOS', '--', 'bash', '-c', shellCommand]);

    launchBackgroundAgentWindow();
  }

  mainWindow?.webContents.send('ai-agent-launch', threadId);
  overlayWindow?.webContents.send('ai-agent-launch', threadId);
  expandMinimizeOverlay(true, false);

  aiagentProcess.stdout.on('data', (data) => {
    const message = data.toString().trimEnd();
    console.log(`[Agent stdout]: ${message}`);
    logMainProcess(`[Agent stdout] ${message}`);
  });
  aiagentProcess.stderr.on('data', (data) => {
    const message = data.toString().trimEnd();
    console.error(`[Agent stderr]: ${message}`);
    logMainProcess(`[Agent stderr] ${message}`);
  });

  aiagentProcess.on('error', err => {
    console.error('âŒ  Agent process failed to start:', err);
    logMainProcess(`[Agent error] ${err?.stack || err}`);
    mainWindow?.webContents.send('trigger-cancel-all-tasks');
  });

  aiagentProcess.on('exit', (code, signal) => {
    console.log(`[Agent exited with code ${code}]`);
    logMainProcess(`[Agent exit] code=${code} signal=${signal}`);
    if (bgAgentWindow) {
      bgAgentWindow.close();
    }
    cleanupBGAgent();
    if (mainWindow?.isMinimized()) {
      mainWindow.restore();
    }
    if (mainWindow) {
      mainWindow.focus();
    }
    mainWindow?.webContents.send('ai-agent-exit');
    overlayWindow?.webContents.send('ai-agent-exit');

    if (code !== 0 || signal) {
      mainWindow?.webContents.send('trigger-cancel-all-tasks');
    }
    aiagentProcess = null;
  });
});

ipcMain.on('stop-ai-agent', () => {
  if (aiagentProcess && !aiagentProcess.killed) {
    kill(aiagentProcess.pid, 'SIGKILL', (err) => {
      if (err) console.error('âŒ Failed to kill agent:', err);
      else console.log('[âœ… Agent forcibly stopped]');
    });
  }
  aiagentProcess = null;
  cleanupBGAgent();
});

const GOOGLE_CLIENT_ID = '756809656093-nammscarkr8bcjavl6qp00fbfikoqo72.apps.googleusercontent.com';
const REDIRECT_URI = 'http://127.0.0.1:36478';

function openUrlInBrowser(targetUrl) {
  const platform = process.platform;
  const command =
    platform === 'win32'
      ? `start "" "${targetUrl}"`
      : platform === 'darwin'
      ? `open "${targetUrl}"`
      : `xdg-open "${targetUrl}"`;
  exec(command);
}

ipcMain.handle('login-with-google', async () => {
  const { codeVerifier, codeChallenge } = generatePKCE();

  const authUrl = `https://accounts.google.com/o/oauth2/v2/auth` +
    `?client_id=${GOOGLE_CLIENT_ID}` +
    `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}` +
    `&response_type=code` +
    `&scope=openid%20email%20profile` +
    `&code_challenge=${codeChallenge}` +
    `&code_challenge_method=S256` +
    `&access_type=offline`;

  openUrlInBrowser(authUrl);

  const appExpress = express();

  return new Promise((resolve, reject) => {
    const server = appExpress.listen(36478, () => {
      console.log('Listening for Google OAuth callback...');
    });

    appExpress.get('/', (req, res) => {
      const code = req.query.code;
      if (!code) {
        res.send('Login failed.');
        server.close();
        return reject('No code received');
      }

      res.send('Login successful! You can close this window.');
      server.close();
      resolve({ code, codeVerifier });
    });
  });
});

const createAppMenu = () => {
  const template = [
    {
      label: 'App',
      submenu: [
        {
          label: 'Background Mode Authentication',
          click: () => {
            if ((aiagentProcess && !aiagentProcess.killed) || (bgAuthProcess && !bgAuthProcess.killed)) {
              return;
            }
            launchBackgroundAuthWindow();
          },
        },
        {
          label: 'Logout',
          click: () => {
            if (overlayWindow) {
              overlayWindow.close();
            }
            mainWindow?.webContents.send('trigger-logout');
          },
        },
        { role: 'quit' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'togglefullscreen' },
        // { role: 'toggledevtools' },
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
};

function startBackgroundAuthServices() {
  bgAuthProcess = spawn('wsl', ['-d', 'NeuralOS', '--', 'bash', '/agent/background_mode_authentication.sh']);

  bgAuthProcess.stdout.on('data', data => {
    console.log(`[BG Auth]: ${data.toString()}`);
  });

  bgAuthProcess.stderr.on('data', data => {
    console.error(`[BG Auth ERROR]: ${data.toString()}`);
  });
}

function cleanupBackgroundAuthServices() {
  try {
    execSync('wsl -d NeuralOS -- bash /agent/background_mode_authentication_cleanup.sh');
    console.log('[BG Auth]: Cleanup script executed.');
  } catch (err) {
    console.error('[BG Auth]: Cleanup failed:', err);
  }

  if (bgAuthProcess) {
    if (!bgAuthProcess.killed) {
      bgAuthProcess.kill('SIGKILL');
    }
  }
  bgAuthProcess = null;
}

function cleanupBGAgent() {
  try {
    execSync('wsl -d NeuralOS -- bash /agent/stop_bg_agent.sh');
    console.log('[BG Agent]: Cleanup script executed.');
  } catch (err) {
    console.error('[BG Agent]: Cleanup failed:', err);
  }

  if (aiagentProcess) {
    if (!aiagentProcess.killed) {
      aiagentProcess.kill('SIGKILL');
    }
  }
}

function waitForNoVNCPortReady(port, timeout = 10000, interval = 300) {
  const deadline = Date.now() + timeout;

  return new Promise((resolve, reject) => {
    const check = () => {
      const req = http.get({ hostname: '127.0.0.1', port, path: '/', timeout: 1000 }, (res) => {
        res.destroy();
        resolve(true); // Port is ready
      });

      req.on('error', (err) => {
        if (Date.now() > deadline) return reject(new Error('Timed out waiting for noVNC'));
        setTimeout(check, interval);
      });

      req.end();
    };

    check();
  });
}

function launchBackgroundAuthWindow() {
  if (backgroundAuthWindow) return;

  startBackgroundAuthServices();

  waitForNoVNCPortReady(39742, 20000)
    .then(() => {
      backgroundAuthWindow = new BrowserWindow({
        width: 1350,
        height: 780,
        title: 'NeuralAgent Background Auth',
        icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
        webPreferences: {
          contextIsolation: true,
          nodeIntegration: false,
          preload: path.join(__dirname, 'electron', 'preload.js'),
        },
      });

      backgroundAuthWindow.loadURL(getFrontendUrl('/background-auth'));

      backgroundAuthWindow.on('closed', () => {
        cleanupBackgroundAuthServices();
        backgroundAuthWindow = null;
      });
    })
    .catch((err) => {
      console.error('âŒ noVNC failed to start:', err);
      cleanupBackgroundAuthServices();
    });
}

function launchBackgroundAgentWindow() {
  if (bgAgentWindow) return;

  waitForNoVNCPortReady(39742, 20000)
    .then(() => {
      bgAgentWindow = new BrowserWindow({
        width: 1350,
        height: 780,
        title: 'NeuralAgent Background Task',
        icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
        webPreferences: {
          contextIsolation: true,
          nodeIntegration: false,
          preload: path.join(__dirname, 'electron', 'preload.js'),
        },
      });

      bgAgentWindow.loadURL(getFrontendUrl('/background-task'));

      bgAgentWindow.on('closed', () => {
        bgAgentWindow = null;
      });
    })
    .catch((err) => {
      console.error('noVNC failed to start:', err);
    });
}

function createWindow() {
  if (mainWindow) return;
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'electron', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    return {
      action: 'allow',
      overrideBrowserWindowOptions: {
        autoHideMenuBar: true,
        webPreferences: {
          nodeIntegration: false,
          contextIsolation: true,
        }
      }
    };
  });

  mainWindow.loadURL(getFrontendUrl());

  mainWindow.on('close', async (e) => {
    if (readyToClose) return;

    e.preventDefault();
    if (mainWindow?.webContents) {
      mainWindow?.webContents.send('trigger-cancel-all-tasks');
    }

    ipcMain.once('cancel-all-tasks-done', () => {
      readyToClose = true;
      mainWindow.close();
    });
  });

  mainWindow.on('closed', () => {
    mainWindow = null;

    if (overlayWindow && !overlayWindow.isDestroyed()) {
      overlayWindow.close();
    }
    if (bgAgentWindow && !bgAgentWindow.isDestroyed()) {
      bgAgentWindow.close();
    }
    if (bgSetupWindow && !bgSetupWindow.isDestroyed()) {
      bgSetupWindow.close();
    }
    if (backgroundAuthWindow && !backgroundAuthWindow.isDestroyed()) {
      backgroundAuthWindow.close();
    }
  });
}

function createOverlayWindow() {
  if (overlayWindow) return;

  const windowWidth = 60;
  const windowHeight = 60;
  const margin = 25;

  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workArea;

  const xPos = screenWidth - windowWidth - margin;
  const yPos = screenHeight - windowHeight - margin;

  overlayWindow = new BrowserWindow({
    width: 60,
    height: 60,
    x: xPos,
    y: yPos,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    webPreferences: {
      preload: path.join(__dirname, 'electron', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  overlayWindow.loadURL(getFrontendUrl('/overlay'));

  overlayWindow.on('closed', () => {
    overlayWindow = null;
  });
}

function expandMinimizeOverlay(expanded, hasSuggestions = false) {
  if (!overlayWindow || overlayWindow.isDestroyed()) return;

  const W = expanded ? 350 : 60;
  const H = expanded ? (hasSuggestions ? 380 : 60) : 60;
  const M = 25;
  const { width: SW, height: SH } = screen.getPrimaryDisplay().workArea;
  const X = SW - W - M;
  const Y = SH - H - M;

  overlayWindow.setBounds({ x: X, y: Y, width: W, height: H }, true);
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

function startCerebro() {
  const launch = () => {
    const isWindows = process.platform === 'win32';
    let cerebroSpawnArgs = [];
    let cerebroSpawnCmd = '';
    let cerebroCwd = '';

    if (isDev) {
      cerebroSpawnCmd = isWindows 
        ? path.join(__dirname, '..', 'backend', 'venv', 'Scripts', 'python.exe')
        : path.join(__dirname, '..', 'backend', 'venv', 'bin', 'python');
      cerebroSpawnArgs = [path.join(__dirname, '..', 'backend', 'run_server.py')];
      cerebroCwd = path.join(__dirname, '..', 'backend');
    } else {
      const execName = isWindows ? 'cerebro.exe' : 'cerebro';
      cerebroSpawnCmd = path.join(process.resourcesPath, execName);
      cerebroCwd = path.dirname(cerebroSpawnCmd);
    }

    cerebroProcess = spawn(cerebroSpawnCmd, cerebroSpawnArgs, {
      cwd: cerebroCwd,
      env: {
        ...process.env,
        PYTHONUTF8: '1',
      },
    });

    cerebroProcess.stdout.on('data', (data) => console.log(`[Cerebro stdout]: ${data}`));
    cerebroProcess.stderr.on('data', (data) => console.error(`[Cerebro stderr]: ${data}`));

    cerebroProcess.on('error', err => {
      console.error('âŒ Cerebro process failed to start:', err);
    });
  };

  const killOldProcess = (callback) => {
    const isWindows = process.platform === 'win32';
    if (isWindows) {
      exec('taskkill /IM cerebro.exe /F', () => callback());
    } else {
      exec('killall cerebro', () => callback());
    }
  };

  if (cerebroProcess && !cerebroProcess.killed) {
    kill(cerebroProcess.pid, 'SIGKILL', () => {
      killOldProcess(launch);
    });
  } else {
    killOldProcess(launch);
  }
}

app.whenReady().then(async () => {
  ensureDeviceId();
  await startFrontendServer();
  
  // Start Cerebro Backend
  startCerebro();

  createWindow();
  if (store.get(constants.ACCESS_TOKEN_STORE_KEY)) {
    createOverlayWindow();
  }
  createAppMenu();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
      createOverlayWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (cerebroProcess && !cerebroProcess.killed) {
    kill(cerebroProcess.pid, 'SIGKILL', (err) => {
      if (err) console.error('âŒ Failed to kill cerebro:', err);
      else console.log('[Cerebro stopped on app exit]');
    });
  }
  if (aiagentProcess && !aiagentProcess.killed) {
    kill(aiagentProcess.pid, 'SIGKILL', (err) => {
      if (err) console.error('âŒ Failed to kill agent:', err);
      else console.log('[Agent stopped on app exit]');
    });
  }
  if (frontendServer) {
    frontendServer.close();
    frontendServer = null;
    frontendBaseUrl = null;
  }
  if (process.platform !== 'darwin') app.quit();
});


