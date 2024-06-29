import threading
import time
from queue import PriorityQueue
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

class Process:
    def __init__(self, process_id, cpu_times, io_times, priority, arrival_time, os, lock , ready_queue):
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
        self.pause_event.set()  # Initially not paused
        self.simulation_time = 0
        self.lock = lock
        self.thread = threading.Thread(target=self.run)
        self.os = os  # Reference to the OS instance
        self.ready_queue = ready_queue

    def __lt__(self, other):
        return self.arrival_time < other.arrival_time

    def run(self):
        while self.current_cpu_index < len(self.cpu_times):
            if self.is_waiting_for_io:
                io_burst_time = self.io_times[self.current_io_index]
                print(f"Process {self.process_id} performing I/O for {io_burst_time}s")
                time.sleep(io_burst_time)
                self.current_io_index += 1
                self.is_waiting_for_io = False
                start_time = self.simulation_time
                self.simulation_time += io_burst_time
                end_time = self.simulation_time
                self.execution_timeline.append((start_time, end_time, 'I/O'))
                # Notify the OS to re-queue the process
                # self.os.requeue_process(self)
                # with self.lock:
                #     self.ready_queue.put((self.simulation_time, self))
                # self.pause_event.clear()  # Pause after I/O
                continue
            
            with self.lock:
                self.ready_queue.put((self.simulation_time, self))

            print(f'before {self.process_id}')
            self.pause_event.wait()  # Wait here if the thread is paused
            print(f'after {self.process_id}')
            if self.current_cpu_index >= len(self.cpu_times):
                break  # All CPU bursts are done

            cpu_burst_time = self.cpu_times[self.current_cpu_index]
            cpu_time_left = min(cpu_burst_time, OS.time_slice)
            self.cpu_times[self.current_cpu_index] -= cpu_time_left

            if self.response_time is None:
                self.response_time = self.simulation_time - self.arrival_time

            start_time = self.simulation_time
            self.simulation_time += cpu_time_left
            end_time = self.simulation_time
            self.execution_timeline.append((start_time, end_time, 'CPU'))

            print(f"Simulating Process {self.process_id}: CPU burst {cpu_time_left}s")
            time.sleep(cpu_time_left)
            self.cpu_usage += cpu_time_left

            if self.cpu_times[self.current_cpu_index] == 0:
                self.current_cpu_index += 1
                if self.current_io_index < len(self.io_times):
                    self.is_waiting_for_io = True

            if self.current_cpu_index < len(self.cpu_times):
                self.pause_event.clear()  # Pause after CPU burst
                continue

        self.completion_time = self.simulation_time
        print(f"Process {self.process_id} completed at {self.simulation_time}s")

class OS:
    time_slice = 4  # Default time slice

    def __init__(self):
        self.processes = []
        self.ready_queue = PriorityQueue()
        self.lock = threading.Lock()
        self.simulation_time = 0
        self.main_thread = threading.Thread(target=self.run)
        self.pause_event = threading.Event()
        self.pause_event.set()  # Initially not paused

    def add_process(self, process):
        with self.lock:
            self.processes.append(process)
            process.simulation_time = self.simulation_time  # Initialize process simulation time
            self.ready_queue.put((process.arrival_time, process))
            process.thread.start()

    def requeue_process(self, process):
        with self.lock:
            print(f"hey im in requeue {process.process_id}")
            self.ready_queue.put((self.simulation_time, process))
            # print(f"Process {process.process_id} re-queued")

    def run(self):
        while any(p.current_cpu_index < len(p.cpu_times) for p in self.processes):
            self.pause_event.wait()  # Wait here if the OS is paused
            if not self.ready_queue.empty():
                _, process = self.ready_queue.get()
                process.pause_event.set()  # Resume the current process
                # with self.lock:
                #     for p in self.processes:
                #         if p.process_id != process.process_id:
                #             p.pause_event.clear()  # Pause other processes

                while process.pause_event.is_set():
                    time.sleep(0.1)  # Wait for the process to finish its current burst or I/O
                    if process.current_cpu_index >= len(process.cpu_times):
                        break
                # print(f'process {process.process_id} id done')
                # process.pause_event.clear()  # Pause the current process after its turn

    def start(self):
        self.main_thread.start()

    def pause(self):
        self.pause_event.clear()
        for process in self.processes:
            process.pause_event.clear()

    def resume(self):
        self.pause_event.set()
        for process in self.processes:
            process.pause_event.set()

    def report(self):
        for process in self.processes:
            print(f"Process ID      : {process.process_id}")
            print(f"Arrival Time    : {process.arrival_time}")
            print(f"Waiting Time    : {process.waiting_time}")
            print(f"Response Time   : {process.response_time}")
            print(f"Completion Time : {process.completion_time}")
            print(f"CPU Usage: {process.cpu_usage}")
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
                start_time = timeline[0]
                end_time = timeline[1]
                color = 'blue' if timeline[2] == 'CPU' else 'orange'
                gnt.broken_barh([(start_time, end_time - start_time)], (10 + idx * 10, 9), facecolors=(color))

        cpu_patch = mpatches.Patch(color='blue', label='CPU Burst')
        io_patch = mpatches.Patch(color='orange', label='I/O Burst')
        plt.legend(handles=[cpu_patch, io_patch])
        plt.title('Process Execution Timeline')
        plt.show()

def read_processes_from_file(filename):
    processes = []
    df = pd.read_csv(filename)

    print(df.head())
    df.columns = df.columns.str.strip()

    for _, row in df.iterrows():
        process_id = int(row['process_id'])
        cpu_times = list(map(int, row['cpu_times'].split(':')))
        io_times = list(map(int, row['io_times'].split(':')))
        priority = int(row['priority'])
        arrival_time = int(row['arrival_time'])
        process = Process(process_id, cpu_times, io_times, priority, arrival_time, MY_OS , MY_OS.lock , MY_OS.ready_queue)
        processes.append(process)
    return processes

# Create an instance of the OS
MY_OS = OS()

# Read processes from the input file
processes = read_processes_from_file('processes.csv')

# Add processes to the OS
for process in processes:
    MY_OS.add_process(process)

# Start the OS
MY_OS.start()
MY_OS.main_thread.join()  # Wait for the main OS thread to complete
MY_OS.report()
MY_OS.visualize()
