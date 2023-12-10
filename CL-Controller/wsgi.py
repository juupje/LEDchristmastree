import sys
print(sys.path)
from cl_controller import create_app

def main(*args, **kwargs):
    print(args, kwargs)
    return create_app(*args, **kwargs)
