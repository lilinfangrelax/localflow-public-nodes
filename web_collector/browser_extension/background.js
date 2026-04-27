class LocalFlowCollector {
  constructor() {
    this.ws = null;
    this.connected = false;
    this.collectTypes = ["page_info", "network", "console"];
    this.maxMessages = 100;
    this.sentCount = 0;
    this.reconnectTimer = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.wsUrl = "ws://localhost:8765";
    this.networkRequests = [];
    this.consoleMessages = [];
    this.domEvents = [];
    this.pageInfo = {};
    this.collecting = false;
  }

  connect(url) {
    if (url) this.wsUrl = url;
    if (this.ws) {
      this.ws.close();
    }

    this.ws = new WebSocket(this.wsUrl);

    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectAttempts = 0;
      this._notifyStatus("connected");
      this._startPing();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "config") {
          this.collectTypes = msg.collect_types || this.collectTypes;
          this.maxMessages = msg.max_messages || this.maxMessages;
          this._notifyConfig(msg);
        }
      } catch (e) {}
    };

    this.ws.onclose = () => {
      this.connected = false;
      this._notifyStatus("disconnected");
      this._stopPing();
      this._tryReconnect();
    };

    this.ws.onerror = () => {
      this._notifyStatus("error");
    };
  }

  disconnect() {
    this._stopPing();
    this._clearReconnect();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
    this._notifyStatus("disconnected");
  }

  startCollecting(tabId) {
    this.collecting = true;
    this.sentCount = 0;
    this.networkRequests = [];
    this.consoleMessages = [];
    this.domEvents = [];

    if (this.collectTypes.includes("page_info")) {
      this._collectPageInfo(tabId);
    }

    if (this.collectTypes.includes("network")) {
      this._startNetworkCapture();
    }

    this._notifyStatus("collecting");
  }

  stopCollecting() {
    this.collecting = false;
    this._stopNetworkCapture();

    if (this.ws && this.connected) {
      this._send({ type: "done" });
    }

    this._notifyStatus("connected");
  }

  sendCollectedData(type, payload) {
    if (!this.connected || this.sentCount >= this.maxMessages) return false;

    const message = {
      type: "data",
      collect_type: type,
      url: payload.url || "",
      timestamp: Date.now(),
      payload: payload
    };

    this._send(message);
    this.sentCount++;
    return true;
  }

  _send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  _startPing() {
    this._stopPing();
    this._pingInterval = setInterval(() => {
      this._send({ type: "ping" });
    }, 30000);
  }

  _stopPing() {
    if (this._pingInterval) {
      clearInterval(this._pingInterval);
      this._pingInterval = null;
    }
  }

  _tryReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    this._clearReconnect();
    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect();
    }, Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000));
  }

  _clearReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  _collectPageInfo(tabId) {
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => {
        return {
          title: document.title,
          url: window.location.href,
          domain: window.location.hostname,
          referrer: document.referrer,
          charset: document.characterSet,
          viewport: {
            width: window.innerWidth,
            height: window.innerHeight
          },
          documentSize: {
            width: document.documentElement.scrollWidth,
            height: document.documentElement.scrollHeight
          },
          meta: Array.from(document.querySelectorAll("meta")).map(m => ({
            name: m.name || m.httpEquiv,
            content: m.content
          })),
          links: Array.from(document.querySelectorAll("a[href]")).slice(0, 50).map(a => ({
            text: a.textContent.trim().substring(0, 100),
            href: a.href
          })),
          images: Array.from(document.querySelectorAll("img")).slice(0, 30).map(img => ({
            src: img.src,
            alt: img.alt,
            width: img.naturalWidth,
            height: img.naturalHeight
          }))
        };
      }
    }).then(results => {
      if (results && results[0] && results[0].result) {
        this.pageInfo = results[0].result;
        this.sendCollectedData("page_info", this.pageInfo);
      }
    }).catch(() => {});
  }

  _startNetworkCapture() {
    if (!chrome.webRequest) return;

    this._networkListener = (details) => {
      if (!this.collecting) return;
      const entry = {
        requestId: details.requestId,
        url: details.url,
        method: details.method || "GET",
        type: details.type,
        tabId: details.tabId,
        timestamp: details.timeStamp
      };
      this.networkRequests.push(entry);
      this.sendCollectedData("network", entry);
    };

    chrome.webRequest.onBeforeRequest.addListener(
      this._networkListener,
      { urls: ["<all_urls>"] },
      ["requestBody"]
    );
  }

  _stopNetworkCapture() {
    if (this._networkListener && chrome.webRequest) {
      chrome.webRequest.onBeforeRequest.removeListener(this._networkListener);
      this._networkListener = null;
    }
  }

  handleConsoleMessage(tabId, message) {
    if (!this.collecting || !this.collectTypes.includes("console")) return;
    this.sendCollectedData("console", {
      tabId: tabId,
      level: message.level,
      text: message.text,
      url: message.url,
      line: message.line,
      timestamp: Date.now()
    });
  }

  handleDomEvent(tabId, eventData) {
    if (!this.collecting || !this.collectTypes.includes("dom_event")) return;
    this.sendCollectedData("dom_event", {
      tabId: tabId,
      ...eventData
    });
  }

  _notifyStatus(status) {
    chrome.runtime.sendMessage({
      type: "status_update",
      status: status,
      sentCount: this.sentCount,
      connected: this.connected,
      collecting: this.collecting
    }).catch(() => {});
  }

  _notifyConfig(config) {
    chrome.runtime.sendMessage({
      type: "config_update",
      config: config
    }).catch(() => {});
  }

  getStatus() {
    return {
      connected: this.connected,
      collecting: this.collecting,
      sentCount: this.sentCount,
      collectTypes: this.collectTypes,
      maxMessages: this.maxMessages,
      wsUrl: this.wsUrl
    };
  }
}

const collector = new LocalFlowCollector();

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case "connect":
      collector.connect(message.url);
      sendResponse({ ok: true });
      break;
    case "disconnect":
      collector.disconnect();
      sendResponse({ ok: true });
      break;
    case "start_collecting":
      collector.startCollecting(message.tabId);
      sendResponse({ ok: true });
      break;
    case "stop_collecting":
      collector.stopCollecting();
      sendResponse({ ok: true });
      break;
    case "get_status":
      sendResponse(collector.getStatus());
      break;
    case "dom_event":
      collector.handleDomEvent(sender.tab?.id, message.event);
      break;
    default:
      sendResponse({ ok: false, error: "Unknown message type" });
  }
  return true;
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    wsUrl: "ws://localhost:8765",
    autoConnect: false,
    collectTypes: ["page_info", "network", "console"]
  });
});
