import sys
sys.path.append("./")
from Config import Config
import warnings
warnings.filterwarnings("ignore")
from autoscaler.Squanler import Squanler

if __name__ == "__main__":

    config = Config()
    controller = Squanler(config)
    controller.start()
