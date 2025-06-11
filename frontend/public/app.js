import { loadONNXModel } from './onnx-loader.js';

const statusEl = document.getElementById('status');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const fileInput = document.getElementById('eegFileInput');
const resultList = document.getElementById('resultHistory');
const WINDOW_SIZE = 128;
const CHANNELS = 4;

let lastFocusValue = 0;
let lastRelaxValue = 0;
let currentUser = localStorage.getItem("username") || "guest";
let loadedEEGData = [];       // загруженные данные
let realDataIndex = 0;        // индекс текущего окна
let eegBuffer = [];           // буфер последних 128 сэмплов
let model = null;             // модель ONNX
let running = false;
let currentSession = [];  // Хранит записи текущей сессии между Start и Stop
let dataInterval = null;
let analysisInterval = null;

// Загрузка файла EEG (json или csv)
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const text = await file.text();
    if (file.name.endsWith('.json')) {
        loadedEEGData = JSON.parse(text);
    } else {
        loadedEEGData = parseCSV(text);
    }

    realDataIndex = 0;
    statusEl.textContent = `Loaded ${loadedEEGData.length} EEG samples.`;
});

function parseCSV(text) {
    const rows = text.trim().split('\n').slice(1); // пропускаем заголовок

    return rows.map(line => {
        const parts = line.split(',').map(p => p.trim());
        if (parts.length < 5) return null;

        // Берём только каналы MV1...MV4 (индексы 1-4)
        const raw = parts.slice(1, 5).map(parseFloat);

        if (raw.some(isNaN)) return null;
        return raw;
    }).filter(Boolean);
}

function normalizeEEGWindow(window) {
    //return window; //отключение нормализации
    const flat = window.flat();
    if (flat.some(v => isNaN(v) || !isFinite(v))) {
        // Можно заменить NaN/Infinity на 0
        return window.map(sample => sample.map(v => (isNaN(v) || !isFinite(v) ? 0 : v)));
    }
    const min = Math.min(...flat);
    const max = Math.max(...flat);
    const range = max - min || 1;

    return window.map(sample =>
        sample.map(v => (v - min) / range * 2 - 1)  // нормализация в [-1,1]
    );
}

function generateRealSample() {
    if (realDataIndex >= loadedEEGData.length) {
        realDataIndex = 0; // зацикливаемся
    }

    const sample = loadedEEGData[realDataIndex];
    realDataIndex++;

    // Нормализуем один сэмпл (масштабируем по значениям за всё окно)
    // Можно отключить, если считаешь ненужным
    const flat = sample.flat();
    const min = Math.min(...flat);
    const max = Math.max(...flat);
    const range = max - min || 1;
    const normalizedSample = sample.map(v => (v - min) / range * 2 - 1);

    return normalizedSample;
}


function updateBuffer(sample) {
    for (let ch = 0; ch < sample.length; ch++) {
        const val = sample[ch];
        if (typeof val !== 'number' || isNaN(val) || !isFinite(val)) {
            sample[ch] = 0;
        }
    }

    eegBuffer.push(sample);
    if (eegBuffer.length > WINDOW_SIZE) {
        eegBuffer.shift();
    }

    // Обновление графика
    for (let ch = 0; ch < CHANNELS; ch++) {
        eegChart.data.datasets[ch].data = eegBuffer.map(row => row[ch]);
    }
    eegChart.update('none');
}

async function addResultToSession(result) {
    const username = localStorage.getItem('username');
    if (!username) {
        console.error("User is not logged in");
        return;
    }
    const now = new Date().toISOString();

    const entry = {
        timestamp: now,
        result: result,
        focus: lastFocusValue,
        relax: lastRelaxValue
    };
    currentSession.push(entry);
}

async function analyzeEEG() {
    if (eegBuffer.length < WINDOW_SIZE) return;

    function prepareInputArray(arr, size = 512) {
        if (arr.length >= size) {
            return arr.subarray(0, size);
        } else {
            const padded = new Float32Array(size);
            padded.set(arr);
            return padded;
        }
    }

    const flatInput = new Float32Array(eegBuffer.flat());
    const inputData = prepareInputArray(flatInput, 512);
    const inputs = { input: inputData };

    try {
        const output = await model.compute(inputs);
        const outputData = output.output.data;
        const [focus, relax] = outputData;

        const result = focus > relax ? 'Concentration' : 'Relaxation';
        statusEl.textContent = `result: ${result}`;

        // Сохраняем значения глобально
        lastFocusValue = focus;
        lastRelaxValue = relax;

        await addResultToSession(result);  // сохраняем в сессию, а не в историю

    } catch (e) {
        console.error('EEG analysis error:', e);
        statusEl.textContent = 'EEG analysis error';
    }
}


// Инициализация графика Chart.js
const eegChartCtx = document.getElementById('eegChart').getContext('2d');
const eegChart = new Chart(eegChartCtx, {
    type: 'line',
    data: {
        labels: Array.from({ length: WINDOW_SIZE }, (_, i) => i),
        datasets: Array.from({ length: CHANNELS }, (_, i) => ({
            label: `Channel ${i + 1}`,
            data: Array(WINDOW_SIZE).fill(0),
            borderColor: `hsl(${(i * 90) % 360}, 80%, 50%)`,
            fill: false,
            tension: 0.1
        }))
    },
    options: {
        animation: false,
        responsive: false,
        scales: {
            y: { beginAtZero: false }
        }
    }
});

// Обработчики кнопок
startBtn.onclick = async () => {
    if (running) return;
    running = true;
    currentSession = [];
    startBtn.disabled = true;
    statusEl.textContent = 'Loading the model...';

    try {
        model = await loadONNXModel('/static/model_512.onnx');  
    } catch (e) {
        statusEl.textContent = 'Error loading the model';
        running = false;
        startBtn.disabled = false;
        return;
    }

    statusEl.textContent = 'An EEG data stream has been initiated...';

    dataInterval = setInterval(() => {
        const newSample = generateRealSample();
        if (newSample) updateBuffer(newSample);
    }, 100);

    analysisInterval = setInterval(analyzeEEG, 1000);
};

stopBtn.onclick = async () => {
    if (!running) return;

    clearInterval(dataInterval);
    clearInterval(analysisInterval);
    dataInterval = null;
    analysisInterval = null;
    running = false;

    statusEl.textContent = 'Analysis halted.';
    startBtn.disabled = false;

    if (currentSession.length > 0 && currentUser !== "guest") {
        const sessionPayload = {
            session_id: crypto.randomUUID(),  // или просто Date.now()
            start: currentSession[0]?.timestamp || new Date().toISOString(),
            end: currentSession[currentSession.length - 1]?.timestamp || new Date().toISOString(),
            entries: currentSession
        };

        await fetch(`/history/${currentUser}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sessionPayload)
        });
        try {
            // Обрати внимание на URL — убрать /session, если сервер не ожидает
            await fetch(`/history/${currentUser}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(currentSession)
            });
        } catch (err) {
            console.error("Error saving a session:", err);
        }
    }

    currentSession = []; // очистить массив для новой сессии
};