#!/home/pi/Documents/environments/flask-wsgi/bin/python3
import sys
print(sys.path)
from cl_controller import app


if __name__=="__main__":
    app.run()