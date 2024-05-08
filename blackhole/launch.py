import sys
import logging
import uvicorn
from blackhole.server import blackhole_api

def start_server():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    uvicorn.run(blackhole_api, host="0.0.0.0", port = 8000)

if __name__ == "__main__":
    start_server()
    