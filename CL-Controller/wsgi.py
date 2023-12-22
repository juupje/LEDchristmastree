from cl_controller import create_app
import multiprocessing
from  ws2811Controller import ws2811Controller

def main(*args, **kwargs):
    print("Main method", multiprocessing.current_process())
    return create_app()

def wsgi_on_starting(server):
    print("On Starting", multiprocessing.current_process())

def wsgi_on_exit(server):
    ws2811Controller._instance.stop()
    print("Exiting")