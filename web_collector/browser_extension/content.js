(function () {
  if (window.__localflowCollectorInjected) return;
  window.__localflowCollectorInjected = true;

  const EVENT_TYPES = ["click", "input", "submit", "scroll", "resize"];
  let observing = false;
  let observer = null;

  function sendDomEvent(eventType, detail) {
    try {
      chrome.runtime.sendMessage({
        type: "dom_event",
        event: {
          eventType: eventType,
          url: window.location.href,
          timestamp: Date.now(),
          ...detail
        }
      });
    } catch (e) {}
  }

  function setupDomListeners() {
    if (observing) return;
    observing = true;

    EVENT_TYPES.forEach((eventType) => {
      document.addEventListener(
        eventType,
        (e) => {
          const detail = {};

          if (eventType === "click") {
            detail.target = e.target.tagName;
            detail.targetId = e.target.id || "";
            detail.targetClass = e.target.className || "";
            detail.targetText = (e.target.textContent || "").substring(0, 100);
            detail.clientX = e.clientX;
            detail.clientY = e.clientY;
          } else if (eventType === "input") {
            detail.target = e.target.tagName;
            detail.targetId = e.target.id || "";
            detail.targetName = e.target.name || "";
            detail.inputType = e.inputType || "";
          } else if (eventType === "submit") {
            detail.target = e.target.tagName;
            detail.targetId = e.target.id || "";
            detail.targetAction = e.target.action || "";
            detail.targetMethod = e.target.method || "";
          } else if (eventType === "scroll") {
            detail.scrollX = window.scrollX;
            detail.scrollY = window.scrollY;
          } else if (eventType === "resize") {
            detail.innerWidth = window.innerWidth;
            detail.innerHeight = window.innerHeight;
          }

          sendDomEvent(eventType, detail);
        },
        { passive: true, capture: true }
      );
    });

    const originalConsole = {};
    ["log", "warn", "error", "info"].forEach((level) => {
      originalConsole[level] = console[level];
      console[level] = function (...args) {
        originalConsole[level].apply(console, args);
        try {
          chrome.runtime.sendMessage({
            type: "dom_event",
            event: {
              eventType: "console",
              level: level,
              text: args
                .map((a) => (typeof a === "object" ? JSON.stringify(a) : String(a)))
                .join(" "),
              url: window.location.href,
              timestamp: Date.now()
            }
          });
        } catch (e) {}
      };
    });
  }

  function setupMutationObserver() {
    if (observer) return;

    observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
          const significant = Array.from(mutation.addedNodes).filter(
            (node) =>
              node.nodeType === Node.ELEMENT_NODE &&
              node.tagName !== "SCRIPT" &&
              node.tagName !== "STYLE"
          );
          if (significant.length > 0) {
            sendDomEvent("dom_mutation", {
              mutationType: "childList",
              addedCount: significant.length,
              targetTag: mutation.target.tagName || ""
            });
          }
        }
      });
    });

    observer.observe(document.body || document.documentElement, {
      childList: true,
      subtree: true
    });
  }

  function start() {
    setupDomListeners();
    setupMutationObserver();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "collect_page_info") {
      const pageInfo = {
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
        meta: Array.from(document.querySelectorAll("meta")).map((m) => ({
          name: m.name || m.httpEquiv,
          content: m.content
        })),
        links: Array.from(document.querySelectorAll("a[href]"))
          .slice(0, 50)
          .map((a) => ({
            text: a.textContent.trim().substring(0, 100),
            href: a.href
          })),
        images: Array.from(document.querySelectorAll("img"))
          .slice(0, 30)
          .map((img) => ({
            src: img.src,
            alt: img.alt,
            width: img.naturalWidth,
            height: img.naturalHeight
          }))
      };
      sendResponse(pageInfo);
      return true;
    }
    if (message.type === "start_collecting") {
      start();
      sendResponse({ ok: true });
      return true;
    }
  });
})();
