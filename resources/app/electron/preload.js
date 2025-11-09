const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  setToken: (token) => ipcRenderer.send('set-token', token),
  getToken: () => ipcRenderer.invoke('get-token'),
  setDarkMode: (isDarkMode) => ipcRenderer.send('set-dark-mode', isDarkMode),
  isDarkMode: () => ipcRenderer.invoke('is-dark-mode'),
  deleteToken: () => ipcRenderer.send('delete-token'),
  setRefreshToken: (refreshToken) => ipcRenderer.send('set-refresh-token', refreshToken),
  getRefreshToken: () => ipcRenderer.invoke('get-refresh-token'),
  deleteRefreshToken: () => ipcRenderer.send('delete-refresh-token'),
  launchAIAgent: (baseURL, threadId, backgroundMode, aiResponse) => ipcRenderer.send('launch-ai-agent', baseURL, threadId, backgroundMode, aiResponse),
  stopAIAgent: () => ipcRenderer.send('stop-ai-agent'),
  onLogout: (callback) => ipcRenderer.on('trigger-logout', callback),
  onAIAgentExit: (callback) => ipcRenderer.on('ai-agent-exit', callback),
  onAIAgentLaunch: (callback) => ipcRenderer.on('ai-agent-launch', (_, threadId, backgroundMode, aiResponse) => callback(threadId, backgroundMode, aiResponse)),
  loginWithGoogle: () => ipcRenderer.invoke('login-with-google'),
  // Guardar adjuntos de imágenes en disco desde el renderer
  saveAttachment: (name, dataURL) => ipcRenderer.invoke('save-attachment', { name, dataURL }),
  expandOverlay: (hasSuggestions) => ipcRenderer.send('expand-overlay', hasSuggestions),
  minimizeOverlay: () => ipcRenderer.send('minimize-overlay'),
  onCancelAllTasksTrigger: (callback) => ipcRenderer.on('trigger-cancel-all-tasks', callback),
  cancelAllTasksDone: () => ipcRenderer.send('cancel-all-tasks-done'),
  getSuggestions: (baseURL) => ipcRenderer.invoke('get-suggestions', baseURL),
  getLastBackgroundModeValue: () => ipcRenderer.invoke('get-last-background-mode-value'),
  startBackgroundSetup: () => ipcRenderer.invoke('start-background-setup'),
  isBackgroundModeReady: () => ipcRenderer.invoke('check-background-ready'),
  onSetupStatus: (cb) => ipcRenderer.on('setup-status', (_, msg) => cb(msg)),
  onSetupProgress: (cb) => ipcRenderer.on('setup-progress', (_, pct) => cb(pct)),
  onSetupComplete: (cb) => ipcRenderer.on('setup-complete', (_, result) => cb(result)),
  testMacOSPermissions: () => ipcRenderer.invoke('test-macos-permissions'),
  hideOverlayTemporarily: (duration) => ipcRenderer.send('hide-overlay-temporarily', duration),
  showOverlay: () => ipcRenderer.send('show-overlay'),
  hideOverlay: () => ipcRenderer.send('hide-overlay'),
  setOverlayClickThrough: (clickThrough) => ipcRenderer.send('set-overlay-click-through', clickThrough),
  openExternal: (url) => ipcRenderer.invoke('open-external', url),
  checkPermissions: () => ipcRenderer.invoke('check-permissions'),
  requestAccessibility: () => ipcRenderer.invoke('request-accessibility'),
  requestScreenRecording: () => ipcRenderer.invoke('request-screen-recording'),
  openSystemPreferences: (permission) => ipcRenderer.invoke('open-system-preferences', permission),
  getAppManagementShown: () => ipcRenderer.invoke('get-app-management-shown'),
  setAppManagementShown: () => ipcRenderer.send('set-app-management-shown'),
  isMacOS: () => process.platform === 'darwin',
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
  downloadUpdate: () => ipcRenderer.invoke('download-update'),
  installUpdate: () => ipcRenderer.invoke('install-update'),
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update-available', (event, info) => callback(info));
  },
  onUpdateNotAvailable: (callback) => {
    ipcRenderer.on('update-not-available', () => callback());
  },
  onDownloadProgress: (callback) => {
    ipcRenderer.on('download-progress', (event, progress) => callback(progress));
  },
  onUpdateDownloaded: (callback) => {
    ipcRenderer.on('update-downloaded', (event, info) => callback(info));
  },
  onUpdateError: (callback) => {
    ipcRenderer.on('update-error', (event, error) => callback(error));
  },
  removeUpdateListeners: () => {
    ipcRenderer.removeAllListeners('update-available');
    ipcRenderer.removeAllListeners('update-not-available');
    ipcRenderer.removeAllListeners('download-progress');
    ipcRenderer.removeAllListeners('update-downloaded');
    ipcRenderer.removeAllListeners('update-error');
  }
});

// ---- Arkaios: asegurar token en el renderer antes de que la app React decida la ruta ----
(() => {
  try {
    const ACCESS_KEY = '_NA_ACCESS_TOK';
    const REFRESH_KEY = '_NA_REFRESH_TOK';
    ipcRenderer.invoke('get-token').then(tok => {
      if (tok) {
        try {
          window.localStorage.setItem(ACCESS_KEY, tok);
          window.dispatchEvent(new CustomEvent('arkaios-token-ready', { detail: { token: tok } }));
        } catch {}
      }
    });
    ipcRenderer.invoke('get-refresh-token').then(rt => {
      if (rt) {
        try { window.localStorage.setItem(REFRESH_KEY, rt); } catch {}
      }
    });
  } catch (e) {}
})();

// ---- Arkaios Monitor: eventos mínimos desde preload para asegurar señalización ----
(() => {
  // Intentar múltiples puertos para evitar desajustes cuando el servidor cambia de 3456 a otro
  const guessPorts = () => {
    // Estándar: forzar uso exclusivo del puerto 3456 para el monitor
    return [3456];
  };
  const send = (type, data = {}) => {
    try {
      const payload = JSON.stringify({ type, ts: Date.now(), ...data });
      const ports = guessPorts();
      for (const p of ports) {
        const url = `http://localhost:${p}/ingest`;
        if (navigator && navigator.sendBeacon) {
          try { navigator.sendBeacon(url, payload); } catch {}
        } else {
          fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload }).catch(()=>{});
        }
      }
    } catch {}
  };

  try { send('preload_loaded'); } catch {}

  try {
    window.addEventListener('DOMContentLoaded', () => {
      send('dom_ready', { title: document.title || '' });
    // ARKAIOS UI hotfix (robusto): reemplazos amplios, atributos, Shadow DOM y override exacto
  (function arkaiosRenameUI(){
    try {
      const replaceAll = (s) => {
        if (!s || typeof s !== 'string') return s;
        return s
          .replace(/Identity\s+Inquiry/gi, 'ARKAIOS')
          .replace(/Inquiri/gi, 'ARKAIOS')
          .replace(/Inquiry/gi, 'ARKAIOS')
          .replace(/Neural\s*Agent/gi, 'Guardian')
          .replace(/NeuralAgent/gi, 'Guardian')
          .replace(/Usuario/gi, 'Guardian')
          .replace(/User/gi, 'Guardian')
          .replace(/Saul\s+Gonzalez/gi, 'Guardian');
      };

      const processTextNode = (node) => {
        try {
          const prev = node.nodeValue;
          const next = replaceAll(prev);
          if (next !== prev) node.nodeValue = next;
        } catch {}
      };

      const processElement = (el) => {
        try {
          ['aria-label','title'].forEach(attr => {
            if (el.hasAttribute && el.hasAttribute(attr)) {
              const v = el.getAttribute(attr);
              const nv = replaceAll(v);
              if (nv !== v) el.setAttribute(attr, nv);
            }
          });
          if (typeof el.innerText === 'string') {
            const v = el.innerText;
            const nv = replaceAll(v);
            if (nv !== v) el.innerText = nv;
          }
        } catch {}
      };

      const processShadowRoot = (root) => {
        try {
          const walker = root.ownerDocument.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
          let n;
          while ((n = walker.nextNode())) processTextNode(n);
          root.querySelectorAll('[aria-label],[title]').forEach(processElement);
        } catch {}
      };

      const run = () => {
        try {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
          let n;
          while ((n = walker.nextNode())) processTextNode(n);

          const selectors = [
            'header', '.sidebar', '.brand',
            '.chakra-badge', '.mantine-Badge-root', '.mantine-Chip-root', '.mantine-Chip-label',
            '[aria-label]', '[title]'
          ];
          document.querySelectorAll(selectors.join(','))
            .forEach(processElement);

          Array.from(document.querySelectorAll('*')).forEach(el => {
            try {
              const txt = (el.innerText || '').trim();
              if (txt && /^Inquiry$/i.test(txt)) el.innerText = 'ARKAIOS';
            } catch {}
          });

          document.querySelectorAll('*').forEach(el => { if (el.shadowRoot) processShadowRoot(el.shadowRoot); });
        } catch (err) { console.warn('ARKAIOS UI hotfix cycle error (preload)', err); }
      };

      run();
      new MutationObserver(() => { try { run(); } catch(e) {} }).observe(document.documentElement, { childList:true, subtree:true, characterData:true });
      console.log('ARKAIOS UI hotfix (preload) active');
    } catch(e) { console.error('ARKAIOS renameUI failed', e); }
  })();

    });
  } catch {}

  try {
    document.addEventListener('paste', (e) => {
      let count = 0;
      try { count = e.clipboardData?.items?.length ?? 0; } catch {}
      send('paste', { count });
    });
  } catch {}

  try {
    setInterval(() => {
      send('heartbeat', { title: document.title || '' });
    }, 5000);
  } catch {}
})();

// ---- Arkaios: Modo local/kill‑switch de paywall y limpieza de sesión ----
(function arkaiosLocalMode(){
  try {
    // Marcar modo local
    try { localStorage.setItem('ARKAIOS_OFFLINE','1'); } catch {}
    const allowOnline = (() => { try { return localStorage.getItem('ARKAIOS_ALLOW_ONLINE_AUTH') === '1'; } catch { return false; } })();

    // 1) Interceptar fetch para endpoints de pricing/limits/usage/subscription y devolver estado PRO local
    const originalFetch = window.fetch;
    const isPricingUrl = (u) => /pricing|plans|plan|billing|stripe|checkout|payment|subscribe|subscription|limits|usage|quota|tier/i.test(u);
    window.fetch = async (input, init) => {
      try {
        const url = (typeof input === 'string') ? input : (input?.url || '')
        const u = url.toString();
        if (!allowOnline && isPricingUrl(u)) {
          const body = {
            plan: 'pro',
            tier: 'pro',
            usage: { tokens: 0, tasks: 0 },
            limits: { daily_tokens: Number.MAX_SAFE_INTEGER, monthly_tokens: Number.MAX_SAFE_INTEGER, tasks: Number.MAX_SAFE_INTEGER },
            subscription: null,
            status: 'ok',
            source: 'arkaios-local'
          };
          return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type':'application/json' } });
        }
      } catch {}
      return originalFetch(input, init);
    };

    // 1.1) Sembrar claves locales comunes para evitar chequeos de límites en la UI
    try {
      const seeds = {
        'NA_PLAN': 'pro',
        'GUARDIAN_PLAN': 'pro',
        'guardian_plan': 'pro',
        'guardian_tier': 'pro',
        'daily_token_limit': String(Number.MAX_SAFE_INTEGER),
        'daily_token_used': '0',
        'monthly_token_limit': String(Number.MAX_SAFE_INTEGER),
        'monthly_token_used': '0'
      };
      Object.keys(seeds).forEach(k=>{ try { localStorage.setItem(k, seeds[k]); } catch{} });
    } catch {}

    // 2) Bloquear canales de red que puedan forzar límite/upgrade
    try {
      const OG_WS = window.WebSocket;
      window.WebSocket = function(url, proto){
        try { if (!allowOnline && typeof url === 'string' && /stripe|billing|pricing|checkout|subscribe|subscription/i.test(url)) {
          console.warn('[Arkaios] WebSocket bloqueado:', url);
          const dummy = { close(){}, send(){}, addEventListener(){}, removeEventListener(){}, readyState: 3 };
          return dummy;
        } } catch {}
        return new OG_WS(url, proto);
      };
    } catch {}
    try {
      const OG_ES = window.EventSource;
      window.EventSource = function(url, cfg){
        try { if (!allowOnline && typeof url === 'string' && /stripe|billing|pricing|checkout|subscribe|subscription/i.test(url)) {
          console.warn('[Arkaios] EventSource bloqueado:', url);
          return { close(){}, addEventListener(){}, removeEventListener(){} };
        } } catch {}
        return new OG_ES(url, cfg);
      };
    } catch {}

    // 3) Eliminar y prevenir modales de “Upgrade Required” en el DOM
    function killPaywallUI(){
      try {
        const selectors = [
          'div[role="dialog"]',
          '.mantine-Modal-root', '.chakra-modal__content', '.modal',
          '.mantine-Modal-content', '.mantine-Paper-root'
        ];
        document.querySelectorAll(selectors.join(',')).forEach(el => {
          try {
            const txt = (el.innerText || '').toLowerCase();
            if (txt.includes('upgrade required') || txt.includes('upgrade to pro') || txt.includes('continue to payment')) {
              el.style.display = 'none';
              el.remove();
            }
          } catch {}
        });
        // Escanear nodos de texto por si el modal usa portales y clases desconocidas
        try {
          const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
          let n;
          while ((n = walker.nextNode())) {
            const val = (n.nodeValue||'').toLowerCase();
            if (val.includes('upgrade required') || val.includes('upgrade to pro') || val.includes('continue to payment')) {
              try {
                const host = (n.parentElement || n.parentNode);
                const dialog = host && (host.closest('div[role="dialog"],.mantine-Modal-root,.chakra-modal__content,.modal,.mantine-Modal-content,.mantine-Paper-root'));
                const target = dialog || host;
                if (target) { target.style.display='none'; target.remove(); }
              } catch {}
            }
          }
        } catch {}
        // Ocultar botones/links
        const btns = Array.from(document.querySelectorAll('button,a')).filter(b => {
          const t = (b.innerText||'').toLowerCase();
          return !allowOnline && (t.includes('upgrade') || t.includes('pricing') || t.includes('payment') || t.includes('continue to payment'));
      });
        btns.forEach(b => { try { b.style.display='none'; b.remove(); } catch {} });
      } catch {}
    }
    killPaywallUI();
    try { new MutationObserver(() => { try { killPaywallUI(); } catch{} }).observe(document.documentElement, { childList:true, subtree:true }); } catch{}
    document.addEventListener('click', (e) => {
      try {
        const t = e.target;
        const txt = (t && t.innerText ? t.innerText.toLowerCase() : '');
        if (!allowOnline && (txt.includes('upgrade') || txt.includes('pricing') || txt.includes('payment'))) {
          e.stopPropagation(); e.preventDefault();
          console.warn('[Arkaios] Click de paywall bloqueado');
        }
      } catch {}
    }, true);

    // 4) Manejar Logout desde menú para limpiar cualquier rastro y recargar en local
    try {
      ipcRenderer.on('trigger-logout', () => {
        try {
          localStorage.clear();
          sessionStorage && sessionStorage.clear && sessionStorage.clear();
        } catch {}
        try { ipcRenderer.send('delete-token'); ipcRenderer.send('delete-refresh-token'); } catch {}
        try { location.reload(); } catch {}
      });
    } catch {}

    console.log('[Arkaios] Kill‑switch local habilitado en preload');
  } catch (e) {
    console.error('[Arkaios] Fallo al habilitar kill‑switch:', e?.message || e);
  }
})();

// ---- Arkaios: Forzar bypass de Login en modo local (robusto) ----
(function arkaiosForceLocalLogin(){
  try {
    const allowOnline = (() => { try { return localStorage.getItem('ARKAIOS_ALLOW_ONLINE_AUTH') === '1'; } catch { return false; } })();
    const ACCESS_KEY = '_NA_ACCESS_TOK';
    const REFRESH_KEY = '_NA_REFRESH_TOK';
    const name = 'Guardian del Fuejo';
    const email = 'arkaios@arkaios.god';
    function b64url(obj){
      try { return Buffer.from(JSON.stringify(obj)).toString('base64').replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); } catch { return 'e30'; }
    }
    const tok = `${b64url({alg:'HS256',typ:'JWT'})}.${b64url({sub:'arkaios-local',name,email,iat:Math.floor(Date.now()/1000),exp:Math.floor(Date.now()/1000)+315576000})}.ARKAIOS`;

    function seedTokens(){
      try {
        localStorage.setItem(ACCESS_KEY, tok);
        localStorage.setItem(REFRESH_KEY, 'ARKAIOS_LOCAL_REFRESH');
        ipcRenderer.send('set-token', tok);
        ipcRenderer.send('set-refresh-token', 'ARKAIOS_LOCAL_REFRESH');
      } catch {}
    }

    function isLoginRoute(){
      try {
        const h = (location.hash||'').toLowerCase();
        const p = (location.pathname||'').toLowerCase();
        return h.includes('login') || /(^|\/)login(\b|\/)/.test(p);
      } catch { return false; }
    }

    function redirectHome(){
      try {
        // Preferir hash router por compatibilidad con build actual
        location.hash = '#/';
      } catch {}
    }

    // Ejecutar al cargar el DOM
    window.addEventListener('DOMContentLoaded', () => {
      try {
        if (!allowOnline && isLoginRoute()) {
          seedTokens();
          redirectHome();
        }
      } catch {}
      // Si queremos auth online y estamos en /login, iniciar automáticamente el flujo Clerk desde el preload
      try {
        if (allowOnline) {
          const noToken = !localStorage.getItem('_NA_ACCESS_TOK');
          const onLogin = () => {
            try { ipcRenderer.invoke('login-with-google'); } catch {}
          };
          if (isLoginRoute() && noToken) {
            onLogin();
          }
          // También escucha señal de éxito para navegar a Home
          ipcRenderer.on('arkaios-auth-success', () => {
            try { redirectHome(); } catch {}
          });
        }
      } catch {}
      // Ocultar contenedores de Login si aparecen
      try {
        const hideLogin = () => {
          try {
            const nodes = Array.from(document.querySelectorAll('h1,h2,h3,p,span,div'));
            const title = nodes.find(n => /(login to neuralagent|login to guardian)/i.test(n.textContent||''));
            if (title) { const root = title.closest('div,section,form'); if (root) { root.style.display='none'; } }
          } catch {}
        };
        hideLogin();
        new MutationObserver(() => { try { hideLogin(); } catch {} }).observe(document.documentElement, { childList:true, subtree:true });
      } catch {}
    }, true);

    // Interceptar clicks y envíos de formularios de Login y Google
    try {
      document.addEventListener('submit', (e) => {
        try {
          const form = e.target;
          const looksLogin = /email|password/i.test((form && form.innerText)||'') || form.querySelector('input[type="email"], input[type="password"]');
          if (!allowOnline && looksLogin) {
            e.preventDefault(); e.stopPropagation();
            seedTokens();
            redirectHome();
          }
        } catch {}
      }, true);
      document.addEventListener('click', (e) => {
        try {
          const t = e.target;
          const txt = ((t && t.innerText) ? t.innerText.toLowerCase() : '');
          const isLoginBtn = txt.includes('login') || txt.includes('continue with google') || txt.includes('google');
          if (!allowOnline && isLoginBtn) {
            e.preventDefault(); e.stopPropagation();
            seedTokens();
            redirectHome();
          }
        } catch {}
      }, true);
    } catch {}

    // Si la app intenta navegar al login después, forzar home
    try {
      const OG_pushState = history.pushState;
      history.pushState = function(){ try { OG_pushState.apply(history, arguments); if (isLoginRoute()) { seedTokens(); redirectHome(); } } catch {} };
      const OG_replaceState = history.replaceState;
      history.replaceState = function(){ try { OG_replaceState.apply(history, arguments); if (!allowOnline && isLoginRoute()) { seedTokens(); redirectHome(); } } catch {} };
      window.addEventListener('hashchange', () => { try { if (!allowOnline && isLoginRoute()) { seedTokens(); redirectHome(); } } catch {} });
      window.addEventListener('popstate', () => { try { if (!allowOnline && isLoginRoute()) { seedTokens(); redirectHome(); } } catch {} });
    } catch {}

    console.log('[Arkaios] Bypass de Login forzado desde preload');
  } catch (e) {
    console.error('[Arkaios] Fallo en bypass de Login (preload):', e?.message || e);
  }
})();

