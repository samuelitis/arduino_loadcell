import asyncio
from bleak import BleakScanner, BleakClient
from openpyxl import Workbook
from openpyxl.writer.excel import ExcelWriter
from datetime import datetime
import sys

WEIGHT_UUID = "00002A57-0000-1000-8000-00805F9B34FB"
BATTERY_UUID = "00002A19-0000-1000-8000-00805F9B34FB"
TIME_UUID = "00002A2B-0000-1000-8000-00805F9B34FB"

experiment_name = input("실험명을 입력하세요 (or press Enter to use 'loadcell'): ")
if not experiment_name:
    experiment_name = "loadcell"

timestamp = datetime.now().strftime("%y%m%d_%H%M")
EXCEL_FILE_PATH = f"./test/{experiment_name}_{timestamp}.xlsx"

wb = Workbook(write_only=True)
ws = wb.create_sheet(title="Loadcell Data")
ws.append(["Timestamp", "Load", "Battery", "Clock Time"])

ROW_BUFFER_LIMIT = 1000
row_count = 0
save_task = None

# BLE 장치 선택
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

# BLE 클라이언트
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
    global row_count, save_task
    try:
        load = int.from_bytes(weight_value, byteorder='little', signed=True) / 1000
        adc_value = int.from_bytes(battery_value, byteorder='little', signed=True) / 1000.0
        adc_value = (adc_value / 1024) * 5.0
        clock_time = int.from_bytes(time_value, byteorder='little', signed=False)
        clock_timestamp = clock_time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        ws.append([timestamp, load, adc_value, clock_timestamp])
        row_count += 1
        print(f"Timestamp: {timestamp} \t|\t Load: {load:.2f} N \t|\t Battery: {adc_value:.2f} \t|\t Clock Time: {clock_timestamp}")

        if row_count >= ROW_BUFFER_LIMIT:
            if save_task is None or save_task.done():
                save_task = asyncio.create_task(save_to_file())
            row_count = 0

    except ValueError:
        print("Received non-numeric data, unable to convert")

async def save_to_file():
    print("Saving data to file...")
    await asyncio.to_thread(wb.save, EXCEL_FILE_PATH)
    print(f"Data saved to {EXCEL_FILE_PATH}")

if __name__ == "__main__":
    try:
        asyncio.run(run_ble_client())
    except KeyboardInterrupt:
        print("Keyboard Interrupt: Saving Excel and closing.")
        if save_task is not None:
            asyncio.run(save_task)
        asyncio.run(save_to_file())
        wb.close()
        sys.exit(0)
