document.addEventListener('DOMContentLoaded', async () => {
  const hostBadge = document.getElementById('hostBadge');
  const statusAlert = document.getElementById('statusAlert');
  const titleInput = document.getElementById('titleInput');
  const priceInput = document.getElementById('priceInput');
  const targetPriceInput = document.getElementById('targetPriceInput');
  const currLabel = document.getElementById('currLabel');
  const notesInput = document.getElementById('notesInput');
  const submitBtn = document.getElementById('submitBtn');
  const form = document.getElementById('addItemForm');

  let extractedData = null;
  const API_ENDPOINT = 'http://localhost:8000/api/v1';

  function showAlert(msg, isError = false) {
    statusAlert.textContent = msg;
    statusAlert.className = `status-msg ${isError ? 'error' : 'success'}`;
  }

  // 1. Get current active browser tab
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id) {
      showAlert('Could not identify active tab', true);
      return;
    }

    const urlObj = new URL(tab.url);
    hostBadge.textContent = urlObj.hostname.replace(/^www\./, '');

    // 2. Request DOM extraction from content script
    chrome.tabs.sendMessage(tab.id, { action: 'EXTRACT_METADATA' }, (response) => {
      if (chrome.runtime.lastError || !response || !response.data) {
        // Fallback: extract from tab info
        titleInput.value = tab.title || '';
        extractedData = {
          product_url: tab.url,
          title: tab.title || 'Product',
          currency: 'INR'
        };
      } else {
        extractedData = response.data;
        titleInput.value = extractedData.title || '';
        if (extractedData.price_minor) {
          priceInput.value = (extractedData.price_minor / 100).toFixed(2);
        }
        if (extractedData.currency) {
          currLabel.textContent = extractedData.currency;
        }
      }
    });
  } catch (err) {
    showAlert(err.message, true);
  }

  // 3. Handle Add to Wishlist submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';

    try {
      // Get stored extension token or prompt
      const storage = await chrome.storage.local.get(['wishtrack_token']);
      const token = storage.wishtrack_token;

      if (!token) {
        showAlert('Please sign in / pair extension from WishTrack web app.', true);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Add to Wishlist';
        return;
      }

      const priceVal = priceInput.value ? Math.round(parseFloat(priceInput.value) * 100) : undefined;
      const targetVal = targetPriceInput.value ? Math.round(parseFloat(targetPriceInput.value) * 100) : undefined;

      const payload = {
        product_url: extractedData.product_url,
        title: titleInput.value.trim(),
        image_url: extractedData.image_url,
        price_minor: priceVal,
        currency: extractedData.currency || 'INR',
        target_price_minor: targetVal,
        notes: notesInput.value.trim() || undefined,
        source: 'extension'
      };

      const res = await fetch(`${API_ENDPOINT}/extension/items`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error?.message || 'Failed to save item');
      }

      showAlert('Product saved to WishTrack!', false);
      submitBtn.textContent = 'Saved!';
      setTimeout(() => window.close(), 1500);
    } catch (err) {
      showAlert(err.message, true);
      submitBtn.disabled = false;
      submitBtn.textContent = 'Add to Wishlist';
    }
  });
});
