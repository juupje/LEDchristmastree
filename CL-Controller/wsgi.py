import logging, os, sys
logging.basicConfig(level=logging.INFO)
from cl_controller.cl_controller import create_app
import multiprocessing
from  cl_controller.ws2811Controller import ws2811Controller
from datetime import datetime

def main(*args, **kwargs):
    print("args:", args, "kwargs:", kwargs)
    os.makedirs("logs", exist_ok=True)
    now = datetime.now()
    time = now.strftime("%d-%m-%Y_%H-%M-%S")
    logging.basicConfig(level=logging.INFO, filename=f"logs/log_{time}.log", filemode='w', format='%(asctime)s - %(levelname)s, %(module)s: %(message)s')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.info("Main method "+ str(multiprocessing.current_process()))
    return create_app()

def wsgi_on_starting(server):
    logging.debug("On Starting " + str(multiprocessing.current_process()))

def wsgi_on_exit(server):
    if ws2811Controller._instance is not None:
        ws2811Controller._instance.stop()
    logging.info("Exiting")