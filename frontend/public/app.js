document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('chart');

    // Проверка на случай, если canvas вдруг не найден
    if (!ctx) {
        console.error('Ошибка: элемент <canvas id="chart"> не найден в DOM');
        return;
    }

    // Создаём график
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['1', '2', '3', '4', '5'],
            datasets: [{
                label: 'EEG Signal',
                data: [0.1, -0.3, 0.5, -0.2, 0.4],
                borderColor: '#3498db',
                tension: 0.1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});