const Storage = {
    get(key, fallback = null) {
        try {
            const raw = localStorage.getItem(key);
            return raw ? JSON.parse(raw) : fallback;
        } catch (e) {
            return fallback;
        }
    },
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn('[Storage] 写入失败:', e.message);
        }
    },
    remove(key) {
        try { localStorage.removeItem(key); } catch (e) {}
    },
    clear() {
        try { localStorage.clear(); } catch (e) {}
    }
};
