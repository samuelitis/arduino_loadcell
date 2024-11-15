import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import time

base_dir = './sample'
csv_files = [f for f in os.listdir(base_dir) if f.endswith('.csv')]

print("CSV 파일 목록:")
for i, file_name in enumerate(csv_files):
    print(f"{i + 1}: {file_name}")

file_index = int(input("시각화할 csv 파일의 번호를 입력해주세요: ")) - 1
selected_file = os.path.join(base_dir, csv_files[file_index])

data = pd.read_csv(selected_file)
clock_time_in_seconds = (data['Clock Time'] - data['Clock Time'].iloc[0]) / 1e6
load = data['Load']

time_scale = 5
min_interval_threshold = 0.01

time_intervals = [0] + [(clock_time_in_seconds.iloc[i + 1] - clock_time_in_seconds.iloc[i]) / time_scale
                        for i in range(len(clock_time_in_seconds) - 1)]

fig, ax = plt.subplots()
ax.set_xlim(0, clock_time_in_seconds.max())
ax.set_ylim(load.min(), load.max() * 1.1)
line, = ax.plot([], [], lw=2)
ax.set_xticks(np.arange(0, clock_time_in_seconds.max(), 60))
ax.grid(which='both', axis='y', linestyle='--', linewidth=0.5)
plt.xlabel('sec')
plt.ylabel('Load')

time.sleep(3)

start_time = time.time()
next_time = start_time

for i in range(1, len(clock_time_in_seconds)):
    current_time = time.time()
    
    line.set_data(clock_time_in_seconds[:i + 1], load[:i + 1])
    
    if clock_time_in_seconds[i] >= 60 * (clock_time_in_seconds[i] // 60):
        print(f"x축 초(sec): {clock_time_in_seconds[i]:.2f} {(time.time() - start_time) * time_scale:.2f}")
    
    if time_intervals[i] < min_interval_threshold:
        continue

    next_time += time_intervals[i]
    sleep_time = max(0, next_time - current_time)
    plt.pause(sleep_time)

plt.show()
print(f"시각화 종료: {(time.time() - start_time) * time_scale:.2f} 초 소요")
