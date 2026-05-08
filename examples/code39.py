"""Example code for code128 library"""


import logging
import sys

from pystrich.code39 import Code39Encoder

logging.getLogger("code39").setLevel(logging.DEBUG)
logging.getLogger("code39").addHandler(logging.StreamHandler(sys.stdout))

if __name__ == "__main__":
    encoder = Code39Encoder(sys.argv[1])
    encoder.save("test.png")
