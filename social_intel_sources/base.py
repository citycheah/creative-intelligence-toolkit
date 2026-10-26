import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseSource(ABC):
    @abstractmethod
    def fetch_data(self) -> list[dict]:
        """
        Fetch data points from the source.
        Returns a list of dictionaries.
        """
        pass
