import logging
import pandas as pd
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseSink(ABC):
    @abstractmethod
    def upload(self, df: pd.DataFrame) -> None:
        """
        Uploads or exports a pandas DataFrame to the sink.
        """
        pass
