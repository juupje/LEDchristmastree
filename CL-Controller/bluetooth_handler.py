from flask_restx import Namespace, Resource
from flask import jsonify, request, Response
import subprocess

bluetooth_api = Namespace("bluetooth", description="Bluetooth related operations")
scan_process = None

def bluetooth_scan_stream():
    """
    Generator function to stream Bluetooth scan results in real-time.
    """
    global scan_process

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
            yield f"data: {line.strip()}\n\n"  # Format for SSE (Server-Sent Events)
    finally:
        if scan_process:
            scan_process.stdin.write('scan off\n')
            scan_process.stdin.flush()
            scan_process.terminate()
            scan_process.wait()

@bluetooth_api.route('/scan', methods=['GET'])
class ScanDevices(Resource):
    def get(self):
        """
        Start scanning for nearby Bluetooth devices and stream results.
        """
        return Response(bluetooth_scan_stream(), mimetype='text/event-stream')

@bluetooth_api.route('/stop-scan', methods=['POST'])
class StopScan(Resource):
    def post(self):
        """
        Stop scanning for Bluetooth devices.
        """
        global scan_process
        if scan_process:
            scan_process.stdin.write('scan off\n')
            scan_process.stdin.flush()
            scan_process.terminate()
            scan_process.wait()
            scan_process = None
            return jsonify({"message": "Scanning stopped"})
        else:
            return jsonify({"error": "No active scan process"}), 400
