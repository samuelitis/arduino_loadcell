import asyncio
import threading
import queue
import csv
from bleak import BleakScanner, BleakClient
from datetime import datetime
import sys

WEIGHT_UUID = "00002A57-0000-1000-8000-00805F9B34FB"
BATTERY_UUID = "00002A19-0000-1000-8000-00805F9B34FB"
TIME_UUID = "00002A2B-0000-1000-8000-00805F9B34FB"

experiment_name = input("실험명을 입력하세요 (or press Enter to use 'loadcell'): ")
if not experiment_name:
    experiment_name = "loadcell"

timestamp = datetime.now().strftime("%y%m%d_%H%M")
CSV_FILE_PATH = f"./test/{experiment_name}_{timestamp}.csv"

data_queue = queue.Queue()

def save_data_to_csv():
    """큐에 있는 데이터를 주기적으로 파일에 저장하는 스레드"""
    with open(CSV_FILE_PATH, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Load", "Battery", "Clock Time"])

        while True:
            data_batch = []
            try:
                while not data_queue.empty():
                    data_batch.append(data_queue.get(timeout=1)) 
            except queue.Empty:
                pass

            if data_batch:
                writer.writerows(data_batch)
                print(f"Saved {len(data_batch)} rows to {CSV_FILE_PATH}")
            
            if not data_batch:
                threading.Event().wait(1)

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
                    process_data(weight_value, battery_value, time_value)
            except Exception as e:
                print(f"An error occurred: {str(e)}")

def process_data(weight_value, battery_value, time_value):
    try:
        load = int.from_bytes(weight_value, byteorder='little', signed=True) / 1000
        adc_value = int.from_bytes(battery_value, byteorder='little', signed=True) / 1000.0
        adc_value = (adc_value / 1024) * 5.0
        clock_time = int.from_bytes(time_value, byteorder='little', signed=False)
        clock_timestamp = clock_time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        data_queue.put([timestamp, load, adc_value, clock_timestamp])
        print(f"Timestamp: {timestamp} \t|\t Load: {load:.2f} N \t|\t Battery: {adc_value:.2f} \t|\t Clock Time: {clock_timestamp}")

    except ValueError:
        print("Received non-numeric data, unable to convert")

if __name__ == "__main__":
    try:
        save_thread = threading.Thread(target=save_data_to_csv, daemon=True)
        save_thread.start()

        asyncio.run(run_ble_client())

    except KeyboardInterrupt:
        print("Keyboard Interrupt: Saving any remaining data and closing.")
        sys.exit(0)
