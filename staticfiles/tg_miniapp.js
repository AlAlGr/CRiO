
window.onload = function() {
    window.Telegram.WebApp.ready();
    const tg = window.Telegram.WebApp;

    // Получаем данные о пользователе из Telegram Mini App
    const user = tg.initDataUnsafe;

    // Отправляем данные на сервер
    fetch('/save_user/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()  // Получаем CSRF токен для защиты от CSRF атак
        },
        body: JSON.stringify({
            user_id: user.id,
            first_name: user.first_name,
            last_name: user.last_name,
            username: user.username,
            avatar_url: user.photo_url
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('User data saved successfully');
        } else {
            console.error('Error saving user data:', data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });

    // Получаем CSRF токен из мета-тега
    function getCsrfToken() {
        const token = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
        return token;
    }
};

}
