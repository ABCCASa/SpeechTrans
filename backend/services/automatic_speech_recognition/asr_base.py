from abc import ABC
from abc import abstractmethod
import torch

class AsrBase(ABC):

    @abstractmethod
    def __init__(self, device: torch.device,  local_files_only: bool = False):
        pass

    @abstractmethod
    def transcribe(self, audio):
        pass
