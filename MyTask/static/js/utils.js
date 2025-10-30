function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

function authenticatedFetch(url, options = {}) {
    const token = localStorage.getItem('token');

    // Установка дефолтных заголовков
    options.headers = {
        ...options.headers,
        'Content-Type': 'application/json',
    };

    // Добавляем Authorization, если токен есть
    if (token) {
        options.headers['Authorization'] = `Token ${token}`;
    }

    return fetch(url, options);
}