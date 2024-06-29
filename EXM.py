def modify_times(cpu_times, io_times):
    new_cpu_times = []
    new_io_times = []
    
    # Iterate through the original CPU times
    for i in range(1, len(cpu_times)):
        if i < len(io_times):
            new_io_times.append(cpu_times[i] - io_times[i-1])
        else:
            new_cpu_times.append(cpu_times[i] - cpu_times[i-1])
    
    # Adjust the first CPU time and the last I/O time
    new_cpu_times.insert(0, cpu_times[0] // 2)
    if len(io_times) > 0:
        new_io_times.append(io_times[-1] // 2)
    
    return new_cpu_times, new_io_times

# Example usage
cpu_times = [0, 7, 15]
io_times = [4, 10]

new_cpu_times, new_io_times = modify_times(cpu_times, io_times)
print("Modified CPU times:", new_cpu_times)
print("Modified I/O times:", new_io_times)
