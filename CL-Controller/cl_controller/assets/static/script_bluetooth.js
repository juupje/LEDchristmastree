function startScan() {
    const eventSource = new EventSource('/bluetooth/scan');

    eventSource.onmessage = function(event) {
        console.log("Received:", event.data);
        // Parse and display the device info as needed
    };

    eventSource.onerror = function(event) {
        console.error("Error:", event);
        eventSource.close();
    };
}

// To stop scanning, call the stop-scan endpoint:
function stopScan() {
    fetch('/bluetooth/stop-scan', { method: 'POST' })
        .then(response => response.json())
        .then(data => console.log(data));
}
