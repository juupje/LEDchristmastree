from cl_controller import create_app
import multiprocessing

def main(*args, **kwargs):
    print("Main method", multiprocessing.current_process())
    return create_app()

def on_starting(server):
    print("On Starting", multiprocessing.current_process())
