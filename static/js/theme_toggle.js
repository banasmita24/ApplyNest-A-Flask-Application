// Lightweight helper to change theme and reload to let server-side templates update
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('theme-toggle');
    if (!toggle) return;
    toggle.addEventListener('change', (e) => {
        const theme = e.target.checked ? 'dark' : 'light';
        fetch(`/set_theme/${theme}`).then(() => location.reload());
    });
});
