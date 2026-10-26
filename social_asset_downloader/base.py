from abc import ABC, abstractmethod

class BaseDownloader(ABC):
    @abstractmethod
    async def download(self, url: str, output_dir: str) -> str | list[str] | None:
        """
        Downloads media from the given URL and saves it to the output directory.

        Args:
            url (str): The social media URL to download.
            output_dir (str): The local directory where the media should be saved.

        Returns:
            str | list[str] | None: The local file path(s) of the downloaded asset(s), or None if download failed.
        """
        pass
