/**
 * Client-side helper to optimize and compress user avatar uploads.
 * Downscales images to max 400x400 while preserving aspect ratio,
 * ensuring fast network transmission and preventing database/payload bloat.
 */
export function processAvatarImage(file, onProcessed, onError) {
  if (!file) return;

  if (!file.type || !file.type.startsWith('image/')) {
    if (onError) onError('Please select an image file (JPEG, PNG, WEBP).');
    return;
  }

  // If file is very small (< 40KB), read directly
  if (file.size < 40 * 1024) {
    const reader = new FileReader();
    reader.onload = (e) => onProcessed(e.target.result);
    reader.onerror = () => onError && onError('Failed to read image.');
    reader.readAsDataURL(file);
    return;
  }

  const reader = new FileReader();
  reader.onerror = () => {
    if (onError) onError('Failed to read file from disk.');
  };

  reader.onload = (readerEvent) => {
    const img = new Image();
    img.onerror = () => {
      // Fallback to raw base64 if Image parsing fails
      onProcessed(readerEvent.target.result);
    };

    img.onload = () => {
      try {
        const MAX_DIM = 400;
        let { width, height } = img;

        if (width > height) {
          if (width > MAX_DIM) {
            height = Math.round((height * MAX_DIM) / width);
            width = MAX_DIM;
          }
        } else {
          if (height > MAX_DIM) {
            width = Math.round((width * MAX_DIM) / height);
            height = MAX_DIM;
          }
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(img, 0, 0, width, height);

        // Export as JPEG at 0.85 quality (~30KB-70KB)
        const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.85);
        onProcessed(compressedDataUrl);
      } catch (err) {
        // Fallback to original data URL if canvas fails
        onProcessed(readerEvent.target.result);
      }
    };

    img.src = readerEvent.target.result;
  };

  reader.readAsDataURL(file);
}

