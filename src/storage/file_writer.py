from __future__ import annotations
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class FileWriterOptions(BaseModel):
    encoding: str = 'utf-8-sig'
    verbose: bool = True
    format: str = "csv"
    output_dir: str = "./output"

class FileWriter(BaseModel):
    _options: FileWriterOptions = Field(alias='options', default_factory=FileWriterOptions)
    _file_path: Optional[str] = None
    _wrote_count: int = 0

    def __init__(self, **data):
        if 'options' in data:
            data['_options'] = data.pop('options')
        super().__init__(**data)

    @property
    def options(self) -> FileWriterOptions:
        return self._options

    def set_file_path(self, file_path: str):
        self._file_path = file_path

    def open(self):
        raise NotImplementedError("Subclasses must implement the open method.")

    def close(self):
        raise NotImplementedError("Subclasses must implement the close method.")

    def write(self, data: Dict[str, Any]):
        raise NotImplementedError("Subclasses must implement the write method.")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

