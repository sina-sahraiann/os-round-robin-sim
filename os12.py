import threading
import time
from queue import PriorityQueue
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

# Function to modify CPU and IO times as needed
def modify_times(cpu_times, io_times):
   new_cpu_times = [io_times[0]]
   new_io_times = []

   # store the timeline between indexes of cpu and io in the new cpu
   for i in range(1, len(cpu_times) - 1):
        new_cpu_times.append(io_times[i] - cpu_times[i])

   # store the time line between each index of i/o and the next index of cpu in the new i/o
   for i in range(len(io_times)):
        new_io_times.append(cpu_times[i + 1] - io_times[i])

   return new_cpu_times, new_io_times

# utility to 
def add_process_interactively(os_instance):
    while True:
        print("Add a new process? (y/n)")
        choice = input().strip().lower()
        if choice == 'n':
            os_instance.exit_program()
            break

        print("Enter process ID:")
        process_id = int(input().strip())
        
        print("Enter CPU times (separated by ':'):")
        cpu_times = list(map(int, input().strip().split(':')))
        
        print("Enter I/O times (separated by ':'):")
        io_times = list(map(int, input().strip().split(':')))
        
        print("Enter priority:")
        priority = int(input().strip())
        
        print("Enter arrival time:")
        arrival_time = int(input().strip())
        
        cpu_times, io_times = modify_times(cpu_times, io_times)
        new_process = Process(process_id, cpu_times, io_times, priority, arrival_time, os_instance, os_instance.lock, os_instance.ready_queue)
        
        os_instance.add_process(new_process)

# Process class to simulate individual processes
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
        self.pause_event.clear()  # Initially paused
        self.simulation_time = 0
        self.lock = lock
        self.thread = threading.Thread(target=self.run)
        self.os = os  # Reference to the OS instance
        self.ready_queue = ready_queue
        self.start_wait = 0
        self.end_wait = 0
        self.currently_waiting = 0
        self.start_sim = time.time()
        
    # Comparison method for priority queue
    def __lt__(self, other):
        return self.priority < other.priority

    # Method to simulate the process execution
    def run(self):
        time.sleep(self.arrival_time)  # Wait until arrival time
        while self.current_cpu_index < len(self.cpu_times) or self.current_io_index < len(self.io_times):
            if self.is_waiting_for_io:
                io_burst_time = self.io_times[self.current_io_index] # currnt i/o burst time
               #  print(f"Process {self.process_id} performing I/O for {io_burst_time}s")
                self.current_io_index += 1 #increament the i/o index
                self.is_waiting_for_io = False
                start_time = time.time()
                time.sleep(io_burst_time)
                self.simulation_time += io_burst_time #update simulation time
                end_time = time.time()
                self.execution_timeline.append((start_time, end_time, 'I/O'))
                if self.current_io_index >= len(self.io_times): # if we are done with i/o 
                    break  # All I/O bursts are done
                continue
            
            with self.lock:
                self.ready_queue.put((self.simulation_time, self))

            self.start_wait = time.time()
            time.sleep(0.1)  # Short sleep to avoid busy waiting
            self.pause_event.wait()  # Wait here if the thread is paused
            self.end_wait = time.time()
            self.currently_waiting = self.end_wait - self.start_wait
            if self.currently_waiting > 0:
                self.waiting_time += self.currently_waiting
                self.simulation_time += self.currently_waiting
                self.execution_timeline.append((self.start_wait, self.end_wait, 'WAIT'))
               #  if self.currently_waiting > 1:
               #      print(f"Process {self.process_id} waiting time is {self.waiting_time // 1}s")
                  
            self.start_wait = 0
            self.end_wait = 0

            # Simulate CPU burst
            cpu_burst_time = self.cpu_times[self.current_cpu_index]
            cpu_time_left = min(cpu_burst_time, OS.time_slice)
            self.cpu_times[self.current_cpu_index] -= cpu_time_left

            start_time = time.time()
            self.simulation_time += cpu_time_left
            time.sleep(cpu_time_left)
            end_time = time.time()
            self.execution_timeline.append((start_time, end_time, 'CPU'))

            if self.response_time is None:
                self.response_time = self.currently_waiting
            self.currently_waiting = 0
            # print(f"Simulating Process {self.process_id}: CPU burst {cpu_time_left}s")
            self.cpu_usage += cpu_time_left

            if self.cpu_times[self.current_cpu_index] == 0:
                self.current_cpu_index += 1
                if self.current_io_index < len(self.io_times):
                    self.is_waiting_for_io = True

            if self.current_cpu_index < len(self.cpu_times):
                self.pause_event.clear()  # Pause after CPU burst
                continue
        
        self.completion_time = self.simulation_time
      #   print(f"Process {self.process_id} completed at {self.simulation_time // 1}s\n-----------------")

# OS class to manage the simulation of processes
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
        self.exit = False

    # Method to add a process to the OS
    def startProcess(self, process):
        with self.lock:
            self.processes.append(process)
            process.simulation_time = self.simulation_time  # Initialize process simulation time
            
    # Method to add a process during runtime
    def add_process(self, process):
        with self.lock:
            self.processes.append(process)
            process.simulation_time = self.simulation_time  # Initialize process simulation time
            process.thread.start()

    # Method to simulate the OS and processes
    def simulate(self):
        for process in self.processes:
            process.thread.start()
        
        # dequeue a process on at a time and allowing them to resume
        while any(p.current_cpu_index < len(p.cpu_times) for p in self.processes) or not self.exit:
            self.pause_event.wait()  # Wait here if the OS is paused
            if not self.ready_queue.empty(): #check that the ready-queue is'nt empty 
                _, process = self.ready_queue.get()
                process.pause_event.set()  # Resume the current process
                while process.pause_event.is_set():
                    time.sleep(0.1)  # Wait for the process to finish its current burst or I/O
                    if process.current_cpu_index >= len(process.cpu_times) and process.current_io_index >= len(process.io_times):
                        break
                process.pause_event.clear()  # Pause the current process after its turn
        
        for process in self.processes:
            process.thread.join()  # Ensure all process threads complete

    # Method to start the OS simulation
    def start(self):
        self.main_thread.start()
        
    def exit_program(self):
       self.exit = True

    # Method to report the results of the simulation
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

    # Method to visualize the process execution timeline
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

            # # Annotate the completion time
            # if process.completion_time is not None:
            #     completion_time = process.completion_time
            #     gnt.annotate(f'{completion_time:.2f}s', xy=(completion_time, 10 + idx * 10 + 5),
            #                  xytext=(completion_time + 2, 10 + idx * 10 + 5),
            #                  arrowprops=dict(arrowstyle='->', lw=1.5))

        # Legend for the plot
        cpu_patch = mpatches.Patch(color='blue', label='CPU Burst')
        io_patch = mpatches.Patch(color='orange', label='I/O Burst')
        wait_patch = mpatches.Patch(color='red', label='Waiting Time')
        # Plot title and display
        plt.legend(handles=[cpu_patch, io_patch, wait_patch])
        plt.title('Process Execution Timeline')
        plt.show()

# Function to read processes from a CSV file and create Process instances
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
        
        cpu_times, io_times = modify_times(cpu_times, io_times)
        
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

# Start the OS simulation
MY_OS.start()

add_process_interactively(MY_OS)

# Wait for the main OS thread to complete
MY_OS.main_thread.join()

# Generate and display the report
MY_OS.report()

# Visualize the process execution timeline
MY_OS.visualize()
