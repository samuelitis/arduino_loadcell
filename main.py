import os
import asyncio
import aiofiles
import csv
from bleak import BleakScanner, BleakClient
from datetime import datetime

WEIGHT_UUID = "00002A57-0000-1000-8000-00805F9B34FB"
BATTERY_UUID = "00002A19-0000-1000-8000-00805F9B34FB"
TIME_UUID = "00002A2B-0000-1000-8000-00805F9B34FB"

experiment_name = input("실험명을 입력하세요 (or press Enter to use 'loadcell'): ")
if not experiment_name:
    experiment_name = "loadcell"

timestamp = datetime.now().strftime("%y%m%d_%H%M")
FOLDER_PATH = f"./test/{experiment_name}_{timestamp}"

if not os.path.exists(FOLDER_PATH):
    os.makedirs(FOLDER_PATH)

ROW_BUFFER_LIMIT = 1000
row_count = 0
file_count = 1

async def select_device():
    print("BLE 장치를 스캔 중입니다...")
    devices = await BleakScanner.discover()
    for index, device in enumerate(devices, start=1):
        name = device.name if device.name else "Unknown"
        print(f"{index}: {name} ({device.address})")

    choice = input("번호를 선택하여 장치를 선택하세요 (예: 1).")
    if choice.isdigit() and int(choice) <= len(devices) and int(choice) > 0:
        return devices[int(choice) - 1]
    print("잘못된 선택입니다.")
    return None

async def run_ble_client():
    device = await select_device()
    if device is None:
        return

    async with BleakClient(device.address, timeout=30.0) as client:
        if client.is_connected:
            print(f"Connected to {device.name} ({device.address})")
            try:
                while True:
                    weight_value = await client.read_gatt_char(WEIGHT_UUID)
                    battery_value = await client.read_gatt_char(BATTERY_UUID)
                    time_value = await client.read_gatt_char(TIME_UUID)
                    await process_data(weight_value, battery_value, time_value)
            except Exception as e:
                print(f"An error occurred: {str(e)}")

async def process_data(weight_value, battery_value, time_value):
    global row_count, file_count
    try:
        load = int.from_bytes(weight_value, byteorder='little', signed=True) / 1000
        adc_value = int.from_bytes(battery_value, byteorder='little', signed=True) / 1000.0
        adc_value = (adc_value / 1024) * 5.0
        clock_time = int.from_bytes(time_value, byteorder='little', signed=False)
        clock_timestamp = clock_time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        print(f"Timestamp: {timestamp} \t|\t Load: {load:.2f} N \t|\t Battery: {adc_value:.2f} \t|\t Clock Time: {clock_timestamp}")

        await write_to_txt([timestamp, load, adc_value, clock_timestamp])

        row_count += 1
        if row_count >= ROW_BUFFER_LIMIT:
            row_count = 0
            file_count += 1

    except ValueError:
        print("Received non-numeric data, unable to convert")

async def write_to_txt(row):
    """현재 파일에 데이터를 한 줄 추가"""
    file_path = os.path.join(FOLDER_PATH, f"{file_count}.txt")
    async with aiofiles.open(file_path, mode='a') as file:
        await file.write(','.join(map(str, row)) + '\n')

async def merge_txt_to_csv():
    """저장된 모든 txt 파일을 하나의 CSV 파일로 병합"""
    csv_file_path = os.path.join(FOLDER_PATH, f"{experiment_name}_{timestamp}.csv")
    with open(csv_file_path, mode='w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Timestamp", "Load", "Battery", "Clock Time"])

        txt_files = sorted([f for f in os.listdir(FOLDER_PATH) if f.endswith(".txt")], key=lambda x: int(x.split('.')[0]))

        for txt_file in txt_files:
            txt_file_path = os.path.join(FOLDER_PATH, txt_file)
            async with aiofiles.open(txt_file_path, mode='r') as file:
                async for line in file:
                    writer.writerow(line.strip().split(','))

if __name__ == "__main__":
    try:
        asyncio.run(run_ble_client())
    except KeyboardInterrupt:
        print("프로그램 종료 중... 모든 txt 파일을 CSV로 병합합니다.")
        asyncio.run(merge_txt_to_csv())
        print(f"CSV 파일로 병합 완료: {FOLDER_PATH}")
