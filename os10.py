import threading
import time
from queue import PriorityQueue
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

class Process:
    def __init__(self, process_id, cpu_times, io_times, priority, arrival_time, os, lock, ready_queue):
        self.process_id = process_id
        self.cpu_times = cpu_times
        self.io_times = io_times
        self.priority = priority
        self.arrival_time = arrival_time
        self.waiting_time = 0
        self.response_time = None
        self.completion_time = None
        self.cpu_usage = 0
        self.current_cpu_index = 0
        self.current_io_index = 0
        self.execution_timeline = []
        self.is_waiting_for_io = False
        self.pause_event = threading.Event()
        self.pause_event.clear()  # Initially not paused
        self.simulation_time = 0
        self.lock = lock
        self.thread = threading.Thread(target=self.run)
        self.os = os  # Reference to the OS instance
        self.ready_queue = ready_queue
        self.start_wait = 0
        self.end_wait = 0
        self.currently_waiting = 0
        self.start_sim = time.time()
        
        
    def __lt__(self, other):
        return self.priority < other.priority

    def run(self):
        time.sleep(self.arrival_time)
        while self.current_cpu_index < len(self.cpu_times):
            if self.is_waiting_for_io:
                io_burst_time = self.io_times[self.current_io_index]
                print(f"Process {self.process_id} performing I/O for {io_burst_time}s")
                self.current_io_index += 1
                self.is_waiting_for_io = False
                start_time = time.time()
                time.sleep(io_burst_time)
                self.simulation_time += io_burst_time
                end_time = time.time()
                self.execution_timeline.append((start_time, end_time, 'I/O'))
                continue

            with self.lock:
                self.ready_queue.put((self.simulation_time, self))

            self.start_wait = time.time()
            time.sleep(0.1)
            self.pause_event.wait()  # Wait here if the thread is paused
            self.end_wait = time.time()
            self.currently_waiting = self.end_wait - self.start_wait
            if self.currently_waiting > 0:
                self.waiting_time += self.currently_waiting
                self.simulation_time += self.currently_waiting
                self.execution_timeline.append((self.start_wait, self.end_wait, 'WAIT'))
                if self.currently_waiting > 1:
                  print(f"Process {self.process_id} waiting time is {self.waiting_time // 1}s")
                  
            self.start_wait = 0
            self.end_wait = 0
            if self.current_cpu_index >= len(self.cpu_times):
                break  # All CPU bursts are done

            cpu_burst_time = self.cpu_times[self.current_cpu_index]
            cpu_time_left = min(cpu_burst_time, OS.time_slice)
            self.cpu_times[self.current_cpu_index] -= cpu_time_left

            start_time = time.time()
            self.simulation_time += cpu_time_left
            time.sleep(cpu_time_left)
            end_time = time.time()
            self.execution_timeline.append((start_time, end_time, 'CPU'))

            if self.response_time is None:
                self.response_time = time.time() - self.start_sim - self.arrival_time
            self.currently_waiting = 0
            print(f"Simulating Process {self.process_id}: CPU burst {cpu_time_left}s")
            self.cpu_usage += cpu_time_left

            if self.cpu_times[self.current_cpu_index] == 0:
                self.current_cpu_index += 1
                if self.current_io_index < len(self.io_times):
                    self.is_waiting_for_io = True

            if self.current_cpu_index < len(self.cpu_times):
                self.pause_event.clear()  # Pause after CPU burst
                continue

        self.completion_time = time.time() - self.start_sim
        print(f"Process {self.process_id} completed at {self.simulation_time // 1}s\n -----------------")

class OS:
    time_slice = 4  # Default time slice

    def __init__(self):
        self.processes = []
        self.ready_queue = PriorityQueue()
        self.lock = threading.Lock()
        self.simulation_time = 0
        self.main_thread = threading.Thread(target=self.simulate)
        self.pause_event = threading.Event()
        self.pause_event.set()  # Initially not paused
        self.start_time = time.time()

    def startProcess(self, process):
        with self.lock:
            self.processes.append(process)
            process.simulation_time = self.simulation_time  # Initialize process simulation time

    def simulate(self):
        for process in self.processes:
           process.thread.start()
        while any(p.current_cpu_index < len(p.cpu_times) for p in self.processes):
            self.pause_event.wait()  # Wait here if the OS is paused
            if not self.ready_queue.empty():
                _, process = self.ready_queue.get()
                current_time = time.time() - self.start_time
                if process.arrival_time <= current_time:
                    process.pause_event.set()  # Resume the current process
                    while process.pause_event.is_set():
                        time.sleep(0.1)  # Wait for the process to finish its current burst or I/O
                        if process.current_cpu_index >= len(process.cpu_times):
                            break
                    process.pause_event.clear()  # Pause the current process after its turn
                else:
                    self.ready_queue.put((process.arrival_time, process))

    def start(self):
        self.main_thread.start()

    def pause(self):
        self.pause_event.clear()
        for process in self.processes:
            process.pause_event.clear()

    def report(self):
        total_cpu_usage = sum(p.cpu_usage for p in self.processes)
        total_simulation_time = time.time() - self.start_time
        print(f"Total Simulation Time : {total_simulation_time:.2f}s")
        print("-----------------------")
        
        for process in self.processes:
            cpu_utilization = (process.cpu_usage / total_cpu_usage) * 100
            print(f"Process ID      : {process.process_id}")
            print(f"Arrival Time    : {process.arrival_time}")
            print(f"Waiting Time    : {process.waiting_time // 1}")
            print(f"Response Time   : {process.response_time // 1}")
            print(f"Completion Time : {process.completion_time // 1}")
            print(f"CPU Usage       : {process.cpu_usage}")
            print(f"CPU Utilization : {cpu_utilization:.2f}%")
            print("-----------------------")


    def visualize(self):
        fig, gnt = plt.subplots()
        gnt.set_xlabel('Time (s)')
        gnt.set_ylabel('Processes')
        gnt.set_yticks([15 + i * 10 for i in range(len(self.processes))])
        gnt.set_yticklabels([f'P{p.process_id}' for p in self.processes])
        gnt.grid(True)

        for idx, process in enumerate(self.processes):
            for timeline in process.execution_timeline:
                start_time = timeline[0] - self.start_time
                end_time = timeline[1] - self.start_time
                color = 'blue' if timeline[2] == 'CPU' else 'orange' if timeline[2] == 'I/O' else 'red'
                gnt.broken_barh([(start_time, end_time - start_time)], (10 + idx * 10, 9), facecolors=(color))

            # Annotate the completion time
            if process.completion_time is not None:
                completion_time = process.completion_time
                gnt.annotate(f'{completion_time:.2f}s', xy=(completion_time, 10 + idx * 10 + 5),
                             xytext=(completion_time + 2, 10 + idx * 10 + 5),
                             arrowprops=dict(arrowstyle='->', lw=1.5))

        cpu_patch = mpatches.Patch(color='blue', label='CPU Burst')
        io_patch = mpatches.Patch(color='orange', label='I/O Burst')
        wait_patch = mpatches.Patch(color='red', label='Waiting Time')
        plt.legend(handles=[cpu_patch, io_patch, wait_patch])
        plt.title('Process Execution Timeline')
        plt.show()

def read_processes_from_file(filename):
    processes = []
    df = pd.read_csv(filename)

   #  print(df.max)
   #  print(df.head())
    df.columns = df.columns.str.strip()

    for _, row in df.iterrows():
        process_id = int(row['process_id'])
        cpu_times = list(map(int, row['cpu_times'].split(':')))
        io_times = list(map(int, row['io_times'].split(':')))
        priority = int(row['priority'])
        arrival_time = int(row['arrival_time'])
        process = Process(process_id, cpu_times, io_times, priority, arrival_time, MY_OS, MY_OS.lock, MY_OS.ready_queue)
        processes.append(process)
    return processes

# Create an instance of the OS
MY_OS = OS()

# Read processes from the input file
processes = read_processes_from_file('processes.csv')

# Add processes to the OS
for process in processes:
    MY_OS.startProcess(process)

MY_OS.start()
# Start the OS
MY_OS.main_thread.join()  # Wait for the main OS thread to complete
MY_OS.report()
MY_OS.visualize()
