// content.js

// Define the URL of your React app.
const ANALYZER_BASE_URL = "http://localhost:3000/"; 

let floatingButton = null; // Reference to the main button element

// Dragging variables
let isDragging = false;
let startX, startY; // Mouse position when drag starts
let initialLeft, initialTop; // Button position when drag starts (relative to viewport)

// Default position if not found in storage. This will be used on first run.
const DEFAULT_BUTTON_POSITION = {
  top: '100px', // 100 pixels from the top of the viewport
  right: '20px' // 20 pixels from the right of the viewport
};

/**
 * Creates and appends the floating button to the YouTube page.
 * Handles button structure (drag handle, text, icon),
 * loads its last saved position, and attaches event listeners.
 */
function createAndAppendButton() {
  // Prevent creating multiple buttons if the script runs again on the same page
  if (document.getElementById('youtube-analyzer-button')) {
    console.log("YouTube Analyzer: Button already exists. Skipping creation.");
    return;
  }

  // 1. Create the main button element
  floatingButton = document.createElement('button');
  floatingButton.id = 'youtube-analyzer-button';
  floatingButton.style.position = 'fixed'; // Essential for floating/fixed position

  // 2. Create a wrapper for the button's main content (text + icon)
  const contentWrapper = document.createElement('div');
  contentWrapper.className = 'button-content-wrapper';
  floatingButton.appendChild(contentWrapper); 

  // 3. Create the PNG icon (now created before text for left placement)
  const buttonIcon = document.createElement('img');
  buttonIcon.className = 'button-icon';
  buttonIcon.src = chrome.runtime.getURL('icon48.png');
  buttonIcon.alt = 'VideoMind';
  contentWrapper.appendChild(buttonIcon);

  // 4. Create the text span for the button (now created after icon)
  const buttonText = document.createElement('span');
  buttonText.className = 'button-text';
  buttonText.textContent = 'VideoMind Analyze';
  contentWrapper.appendChild(buttonText);

 //5.Create the drag handle
  const dragHandle = document.createElement('div');
  dragHandle.className = 'drag-handle';
  contentWrapper.appendChild(dragHandle);

  // 6. Load the button's last saved position from Chrome storage
  chrome.storage.local.get(['analyzerButtonPosition'], function(result) {
    if (result.analyzerButtonPosition) {
      floatingButton.style.top = result.analyzerButtonPosition.top;
      floatingButton.style.left = result.analyzerButtonPosition.left;
      floatingButton.style.right = 'auto';
    } else {
      // If no saved position, apply the default position defined above
      floatingButton.style.top = DEFAULT_BUTTON_POSITION.top;
      floatingButton.style.right = DEFAULT_BUTTON_POSITION.right;
    }
  });

  // 7. Attach the click listener to the *main button* for analysis
  floatingButton.addEventListener('click', (e) => {
    if (isDragging || e.target === dragHandle || dragHandle.contains(e.target)) {
        console.log("YouTube Analyzer: Click originated from drag handle or was part of a drag. Preventing analysis.");
        return; // Do not proceed with opening the analyzer
    }

    const videoElement = document.querySelector('video'); // Find the main video element on the page
    if (videoElement && !videoElement.paused) {
      videoElement.pause(); // Call the pause() method on the video element
      console.log("YouTube Analyzer: YouTube video paused.");
    } else {
      console.log("YouTube Analyzer: Video not found or already paused/ended.");
    }

    const videoUrl = window.location.href;
    const encodedVideoUrl = encodeURIComponent(videoUrl);
    const analyzerFullUrl = `${ANALYZER_BASE_URL}?videoUrl=${encodedVideoUrl}`;
    console.log("YouTube Analyzer: Opening new window for:", analyzerFullUrl);
    chrome.runtime.sendMessage({ action: "openAnalyzer", url: analyzerFullUrl });
  });

  // 8. --- DRAGGING LOGIC (attached to the dragHandle) ---
  dragHandle.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;

    isDragging = true;
    dragHandle.style.cursor = 'grabbing'; // Change cursor on the drag handle
    floatingButton.style.cursor = 'grabbing'; // Also change overall button cursor during drag

    // Record the initial mouse position
    startX = e.clientX;
    startY = e.clientY;

    // Get the button's current position (relative to the viewport)
    const rect = floatingButton.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop = rect.top;

    // Prevent default browser actions like text selection during drag
    e.preventDefault();
    // Stop event propagation to prevent the main button's click listener from firing
    e.stopPropagation();

    // Attach global mousemove and mouseup listeners to the document
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  });

  // Function to handle mouse movement during a drag
  function onMouseMove(e) {
    if (!isDragging) return;

    // Calculate the mouse displacement
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    // Calculate the new position for the button
    let newLeft = initialLeft + dx;
    let newTop = initialTop + dy;

    // Keep the button within the viewport boundaries
    newLeft = Math.max(0, Math.min(newLeft, window.innerWidth - floatingButton.offsetWidth));
    newTop = Math.max(0, Math.min(newTop, window.innerHeight - floatingButton.offsetHeight));

    // Apply the new position
    floatingButton.style.left = `${newLeft}px`;
    floatingButton.style.top = `${newTop}px`;
    floatingButton.style.right = 'auto'; // Ensure 'right' is auto when 'left' is explicitly set
  }

  // Function to handle mouse button release (ends the drag)
  function onMouseUp(e) {
    if (!isDragging) return; // Only process if dragging was active

    isDragging = false;
    dragHandle.style.cursor = 'grab';
    floatingButton.style.cursor = 'pointer';

    // Remove the global mousemove and mouseup listeners
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);

    // Save the final position to Chrome storage for persistence
    chrome.storage.local.set({
      analyzerButtonPosition: {
        top: floatingButton.style.top,
        left: floatingButton.style.left
      }
    });
  }

  // 9. Append the entire floating button to the document body
  document.body.appendChild(floatingButton);
  console.log("YouTube Analyzer: Floating button created and appended.");
}

function removeButton() {
    if (floatingButton && floatingButton.parentNode) {
        floatingButton.parentNode.removeChild(floatingButton);
        floatingButton = null; // Clear the reference
        console.log("YouTube Analyzer: Button removed from page.");
    }
}

/**
 * Initializes the button: creates it if on a watch page, removes it otherwise.
 * Called on initial load and on YouTube's navigation events.
 */
function initializeButton() {
  // Check if the current URL path starts with '/watch' (indicates a YouTube video page)
  if (window.location.pathname.startsWith('/watch')) {
    if (document.querySelector('ytd-watch-flexy')) {
      createAndAppendButton();
    }
  } else {
    removeButton();
  }
}

// --- Dynamic Page Handling with MutationObserver and YouTube's Custom Event ---

const observer = new MutationObserver(mutations => {
  mutations.forEach(mutation => {
    // Look for changes in the main content area (childList or subtree changes)
    if (mutation.type === 'childList' || mutation.type === 'subtree') {
      // If a video player element is present and we're on a watch page, initialize the button
      if (document.querySelector('ytd-watch-flexy') && window.location.pathname.startsWith('/watch')) {
        initializeButton();
      } else if (!document.querySelector('ytd-watch-flexy') && floatingButton) {
        // If the video player disappears (e.g., navigating to homepage) and button exists, remove it
        removeButton();
      }
    }
  });
});

// Find a high-level element that contains most of YouTube's dynamic content
const pageManager = document.querySelector('ytd-page-manager');
if (pageManager) {
  // Start observing this element for changes (child nodes added/removed, or changes within subtrees)
  observer.observe(pageManager, { childList: true, subtree: true });
  console.log("YouTube Analyzer: MutationObserver started on player for dynamic content.");
} else {
  console.warn("YouTube Analyzer: Could not find '#player' to observe. Dynamic updates might not be detected reliably.");
}

// Initial call to set up the button when the content script first loads
initializeButton();
console.log("YouTube Analyzer: Initial button setup attempted.");

// Listen for YouTube's custom navigation event, which is fired when navigating between videos
document.addEventListener('yt-navigate-finish', initializeButton);
console.log("YouTube Analyzer: Listening for 'yt-navigate-finish' event for page transitions.");