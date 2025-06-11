import pandas as pd
import numpy as np

# Чтение CSV
df = pd.read_csv("S001E01.csv")

# Удаляем столбец времени
eeg_data = df.drop(columns=['time'])

# Параметры
sampling_rate = 128
window_size = 128  # 1 секунда
step_size = 64     # окно со смещением 0.5 сек (оверлап)

X = []
y = []

for start in range(0, len(eeg_data) - window_size, step_size):
    window = eeg_data.iloc[start:start+window_size].values.flatten()
    X.append(window)
    
    # Фейковая разметка:
    # первые 30 секунд — расслабление (label 0)
    # следующие 30 секунд — концентрация (label 1)
    if start < 60 * sampling_rate:
        y.append(0)
    else:
        y.append(1)

X = np.array(X)
y = np.array(y)

# Сохраняем
np.save("X_fake.npy", X)
np.save("y_fake.npy", y)

print(f"Сохранено: {X.shape[0]} окон, {X.shape[1]} признаков")
