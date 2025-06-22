// background.js (Service Worker)

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "openAnalyzer") {
    const analyzerUrl = message.url;
    // Open in a new window, similar to a pop-up
    chrome.windows.create({
      url: analyzerUrl,
      type: "normal",
      state: "maximized"
    });
  }
});