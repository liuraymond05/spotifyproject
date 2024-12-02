function setTheme(theme) {
    document.cookie = `theme=${theme}; path=/; max-age=31536000`; // Save for 1 year
    applyTheme(theme);
}

function applyTheme(theme) {
    document.body.className = theme; // Apply the selected theme
}

function getThemeFromCookie() {
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith('theme='))
        ?.split('=')[1];
    return cookieValue || 'light-mode'; // Default to 'light-mode'
}

window.onload = function () {
    const theme = getThemeFromCookie();
    applyTheme(theme);

    // Update the dropdown value
    const colorModeSelect = document.getElementById('color-mode');
    if (colorModeSelect) {
        colorModeSelect.value = theme;
    }
};
