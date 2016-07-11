from Station import StationManager
from Processes import ProcessManager
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
handler = logging.FileHandler('processingManager.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s p%(process)s {%(pathname)s:%(lineno)d} - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class ProcessingManager:
    def __init__(self):
        qc_definitions = ProcessManager()
        # Alternatively, insert manually here
        # station_manager = StationManager(qc_definitions, 2016, 4)
        station_manager = StationManager(qc_definitions)


