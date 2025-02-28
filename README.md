CPU stress test with WEB GUI

- Multiprocessing:
The code creates multiple processes (equal to the number of specified cores) using multiprocessing.Process. Each process is assigned to a specific core using cpu_affinity.
- Computational Load:
In each worker task, the heavy_kernel function is executed, optimized with numba for rapid execution of mathematical operations (sine, cosine, tangent). This generates an intensive floating-point computation load.
- Progress Monitoring:
Each process reports its results (e.g., the number of completed iterations) through a Queue. These data are then sent to the client via WebSocket.
- Asynchrony and Flexibility:
Threads and processes operate independently, ensuring parallel execution of the benchmark and data exchange with the client.

Interface:
