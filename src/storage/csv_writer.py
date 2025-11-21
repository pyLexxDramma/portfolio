from __future__ import annotations
import csv
import logging
import os
from typing import Any, Dict

from src.storage.file_writer import FileWriter, FileWriterOptions
from src.config.settings import Settings

logger = logging.getLogger(__name__)

class CSVWriter(FileWriter):
    def __init__(self, settings: Settings):
        if hasattr(settings, 'app_config'):
            writer_opts = settings.app_config.writer
        else:
            writer_opts = settings.writer

        file_writer_options = FileWriterOptions(
            encoding=writer_opts.encoding,
            verbose=writer_opts.verbose,
            format=writer_opts.format,
            output_dir=writer_opts.output_dir
        )
        super().__init__(options=file_writer_options)
        self.fieldnames: list = None
        self.header_written: bool = False
        self.file_handle = None
        self.writer = None

    def open(self):
        if not self.file_path:
            raise ValueError("File path is not set. Use set_file_path() first.")

        output_dir = os.path.dirname(self.file_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")

        try:
            self.file_handle = open(self.file_path, 'w', newline='', encoding=self.options.encoding)
            self.writer = csv.writer(self.file_handle)
            logger.info(f"CSV file opened: {self.file_path}")
        except Exception as e:
            logger.error(f"Error opening CSV file {self.file_path}: {e}", exc_info=True)
            raise

    def close(self):
        if self.file_handle:
            self.file_handle.close()
            logger.info(f"CSV file closed. Wrote {self.wrote_count} records.")

    def write(self, data: Dict[str, Any]):
        if not self.writer:
            logger.error("CSV writer not initialized. Call open() first.")
            return

        if self.fieldnames is None:
            self.fieldnames = list(data.keys())
            if not self.header_written:
                self.writer.writerow(self.fieldnames)
                self.header_written = True

        row = [data.get(field) for field in self.fieldnames]
        self.writer.writerow(row)
        self.wrote_count += 1

