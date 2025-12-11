from flask_restx import Namespace, Resource
from flask import jsonify, request, Response, render_template
import subprocess
import threading
import time
import re

bluetooth_api = Namespace("bluetooth", description="Bluetooth related operations")
scan_process = None
stop_scan = False
lock = threading.Lock()

def clean_bluetooth_output(raw_output):
    """
    Clean the raw Bluetooth output by removing ANSI escape codes
    and extracting relevant device information.
    """
    # Remove ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    cleaned_lines = [ansi_escape.sub('', line) for line in raw_output]

    # Extract devices
    devices = []
    for line in cleaned_lines:
        # Match lines containing discovered devices (e.g., "[NEW] Device MAC_ADDRESS Device_Name")
        match = re.search(r'\[NEW\] Device ([0-9A-F:]{17}) (.+)', line)
        if match:
            mac_address = match.group(1)
            name = match.group(2)
            devices.append({"mac_address": mac_address, "name": name})

    return devices

def bluetooth_scan_stream():
    """
    Generator function to stream Bluetooth scan results in real-time.
    """
    global scan_process, stop_scan

    try:
        # Start bluetoothctl in a subprocess
        scan_process = subprocess.Popen(
            ['bluetoothctl'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffering
        )

        # Send 'scan on' command
        scan_process.stdin.write('scan on\n')
        scan_process.stdin.flush()

        # Read and yield output line-by-line
        for line in iter(scan_process.stdout.readline, ''):
            if stop_scan:
                break
            yield f"data: {line.strip()}\n\n"  # Format for SSE (Server-Sent Events)
    finally:
        with lock:
            if scan_process:
                scan_process.stdin.write('scan off\nexit\n')
                scan_process.stdin.flush()
                scan_process.terminate()
                scan_process.wait()

@bluetooth_api.route('/scan', methods=['GET'])
class ScanDevices(Resource):
    def get(self):
        global scan_process, stop_scan
        gen = bluetooth_scan_stream()
        devices = []
        def gather_data():
            for line in gen:
                devices.append(line)
        thread = threading.Thread(target=gather_data)
        thread.start()
        time.sleep(15)
        stop_scan = True
        time.sleep(1)
        with lock:
            if scan_process:
                scan_process.stdin.write('scan off\nexit\n')
                scan_process.stdin.flush()
                scan_process.terminate()
                scan_process.wait()
        thread.join()
        devices = clean_bluetooth_output(devices)
        return jsonify(devices)
        #return Response(bluetooth_scan_stream(), mimetype='text/event-stream')

@bluetooth_api.route('/stop-scan', methods=['POST'])
class StopScan(Resource):
    def post(self):
        """
        Stop scanning for Bluetooth devices.
        """
        if scan_process:
            scan_process.stdin.write('scan off\n')
            scan_process.stdin.flush()
            scan_process.terminate()
            scan_process.wait()
            scan_process = None
            return jsonify({"message": "Scanning stopped"})
        else:
            return jsonify({"error": "No active scan process"}), 400
        
def render_webpage():
    return render_template("bluetooth.html")