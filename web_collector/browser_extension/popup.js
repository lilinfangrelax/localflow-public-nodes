document.addEventListener("DOMContentLoaded", () => {
  const wsUrlInput = document.getElementById("wsUrl");
  const btnConnect = document.getElementById("btnConnect");
  const btnDisconnect = document.getElementById("btnDisconnect");
  const btnStartCollect = document.getElementById("btnStartCollect");
  const btnStopCollect = document.getElementById("btnStopCollect");
  const statusBar = document.getElementById("statusBar");
  const statusText = document.getElementById("statusText");
  const sentCountEl = document.getElementById("sentCount");
  const maxMessagesEl = document.getElementById("maxMessages");
  const chkPageInfo = document.getElementById("chkPageInfo");
  const chkNetwork = document.getElementById("chkNetwork");
  const chkConsole = document.getElementById("chkConsole");
  const chkDomEvent = document.getElementById("chkDomEvent");

  function updateUI(status) {
    const isConnected = status.connected;
    const isCollecting = status.collecting;

    statusBar.className = "status-bar " + (
      isCollecting ? "collecting" :
      isConnected ? "connected" : "disconnected"
    );
    statusText.textContent = isCollecting
      ? "收集中..."
      : isConnected
      ? "已连接"
      : "未连接";

    btnConnect.disabled = isConnected;
    btnDisconnect.disabled = !isConnected;
    btnStartCollect.disabled = !isConnected || isCollecting;
    btnStopCollect.disabled = !isCollecting;
    sentCountEl.textContent = status.sentCount || 0;
    maxMessagesEl.textContent = status.maxMessages || 100;
  }

  function getStatus() {
    chrome.runtime.sendMessage({ type: "get_status" }, (response) => {
      if (chrome.runtime.lastError || !response) {
        updateUI({ connected: false, collecting: false, sentCount: 0, maxMessages: 100 });
        return;
      }
      updateUI(response);
      wsUrlInput.value = response.wsUrl || "ws://localhost:8765";
    });
  }

  btnConnect.addEventListener("click", () => {
    const url = wsUrlInput.value.trim();
    if (!url) return;
    chrome.runtime.sendMessage({ type: "connect", url: url }, () => {
      setTimeout(getStatus, 500);
    });
  });

  btnDisconnect.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "disconnect" }, () => {
      setTimeout(getStatus, 200);
    });
  });

  btnStartCollect.addEventListener("click", () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tabId = tabs[0]?.id;
      if (!tabId) return;
      chrome.runtime.sendMessage({ type: "start_collecting", tabId: tabId }, () => {
        setTimeout(getStatus, 300);
      });
    });
  });

  btnStopCollect.addEventListener("click", () => {
    chrome.runtime.sendMessage({ type: "stop_collecting" }, () => {
      setTimeout(getStatus, 200);
    });
  });

  chrome.runtime.onMessage.addListener((message) => {
    if (message.type === "status_update") {
      updateUI({
        connected: message.connected,
        collecting: message.collecting,
        sentCount: message.sentCount
      });
    }
    if (message.type === "config_update") {
      if (message.config.max_messages) {
        maxMessagesEl.textContent = message.config.max_messages;
      }
    }
  });

  getStatus();
});
