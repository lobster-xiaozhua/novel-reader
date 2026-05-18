let fontSize = parseInt(localStorage.getItem('reader-font-size') || '18');
let saveTimer = null;

function updateFontSize() {
    document.getElementById('readerContent').style.fontSize = fontSize + 'px';
    document.getElementById('fontSizeDisplay').textContent = fontSize;
    localStorage.setItem('reader-font-size', fontSize);
}

function increaseFontSize() {
    if (fontSize < 28) {
        fontSize += 2;
        updateFontSize();
    }
}

function decreaseFontSize() {
    if (fontSize > 12) {
        fontSize -= 2;
        updateFontSize();
    }
}

function saveProgress() {
    if (typeof window.chapterId === 'undefined') return;
    const position = window.scrollY;

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    fetch(`/chapters/${window.bookId}/save-progress/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `chapter_id=${window.chapterId}&position=${position}`
    }).catch(() => {});
}

function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveProgress, 2000);
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    updateFontSize();
    window.addEventListener('scroll', scheduleSave);
    window.addEventListener('beforeunload', saveProgress);
});
