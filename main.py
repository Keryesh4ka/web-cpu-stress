import time
import math
import os
import psutil
from flask import Flask, render_template
from flask_socketio import SocketIO
from numba import njit
import threading
from multiprocessing import Process, Event, freeze_support, Queue
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Глобальные переменные для управления бенчмарком
benchmark_processes = []  # Список запущенных процессов-бенчмаркеров
benchmark_stop_event = None  # Сигнал для остановки процессов

# Глобальные переменные для логгера вычислений
calc_queue = None  # Очередь для передачи результатов вычислений из процессов
calc_log_thread = None  # Поток, считывающий данные из calc_queue
calc_log_stop_event = None  # Сигнал для остановки логгера

# Информация, получаемая один раз при запуске
CPU_MODEL = f"{psutil.cpu_count(logical=False)}-Core CPU @ {psutil.cpu_freq().max / 1000:.2f}GHz" if psutil.cpu_freq() else "Неизвестно"
BASE_FREQUENCY = psutil.cpu_freq().max / 1000 if psutil.cpu_freq() else None

@app.route('/')
def index():
    max_cores = psutil.cpu_count(logical=True) or 1
    return render_template('index.html', max_cores=max_cores)

def system_monitor():
    """
    Фоновый поток мониторинга. Отправляет данные о состоянии системы.
    """
    # Поток мониторинга
    while True:
        data = {
            'cpu': psutil.cpu_percent(interval=None),
            'cpu_perc': psutil.cpu_percent(interval=None, percpu=True),
            'ram': psutil.virtual_memory()
        }
        socketio.emit('system_update', data)
        time.sleep(0.1)

@njit(fastmath=True, nogil=True)
def heavy_kernel(n):
    """
    Однопоточная вычислительная функция.
    """
    total = 0.0
    for i in range(n):
        total += math.sin(i) * math.cos(i / 100.0) + math.tan(i / 1000.0)
    return total

def benchmark_worker(core, stop_event, calc_queue):
    """
    Задача для одного ядра процессора.
    """
    try:
        current = psutil.Process()
        current.cpu_affinity([core])
    except Exception as e:
        print(f"Unable to set affinity to core {core}: {e}")
    
    iterations = 10_000_000
    while not stop_event.is_set():
        result = heavy_kernel(iterations)
        now = datetime.now().strftime("%H:%M:%S")
        msg = f"[{now}] Core {core}: heavy_kernel({iterations}) = {result}"
        try:
            calc_queue.put(msg)
        except Exception:
            pass

def benchmark_result_logger():
    """
    Логирование результатов вычислений.
    """
    global calc_queue, calc_log_stop_event
    while not calc_log_stop_event.is_set():
        try:
            msg = calc_queue.get(timeout=0.1)
            socketio.emit('calc_log', {'msg': msg})
        except Exception:
            continue

@socketio.on('start_benchmark')
def handle_start_benchmark(data):
    """
    Запуск бенчмарка.
    """
    global benchmark_processes, benchmark_stop_event, calc_log_thread, calc_log_stop_event, calc_queue
    if benchmark_processes:
        socketio.emit('benchmark_status', {'status': 'already_started'})
        return

    max_cores = psutil.cpu_count(logical=True) or 1
    requested_cores = min(int(data.get('cores', max_cores)), max_cores)

    benchmark_stop_event = Event()
    benchmark_processes = []
    calc_queue = Queue()

    for core in range(requested_cores):
        p = Process(target=benchmark_worker, args=(core, benchmark_stop_event, calc_queue))
        p.daemon = True
        benchmark_processes.append(p)
        p.start()

    calc_log_stop_event = Event()
    calc_log_thread = threading.Thread(target=benchmark_result_logger)
    calc_log_thread.daemon = True
    calc_log_thread.start()

    socketio.emit('benchmark_status', {'status': 'started', 'cores': requested_cores})

@socketio.on('stop_benchmark')
def handle_stop_benchmark():
    """
    Остановка бенчмарка.
    """
    global benchmark_processes, benchmark_stop_event, calc_log_thread, calc_log_stop_event, calc_queue
    if benchmark_stop_event is not None:
        benchmark_stop_event.set()
    for p in benchmark_processes:
        p.join(timeout=1)
    benchmark_processes = []
    if calc_log_stop_event is not None:
        calc_log_stop_event.set()
    if calc_log_thread is not None:
        calc_log_thread.join(timeout=1)
    calc_log_thread = None
    calc_log_stop_event = None
    calc_queue = None
    socketio.emit('benchmark_status', {'status': 'stopped'})

if __name__ == '__main__':
    freeze_support()
    monitor_thread = threading.Thread(target=system_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    socketio.run(app, host='0.0.0.0', port=5000)
