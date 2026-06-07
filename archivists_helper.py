import csv
import os
from hashlib import sha256
import pathlib
import bagit
from datetime import datetime

# CHANGELOG
class LogWriter:
    def __init__(self, project_name:str, dt_format:str = '%Y%m%d-%H:%M:%S.%f')->None:
        self.project_name = project_name
        self.log_file = self.project_name + 'changelog.csv'
        self.dt_format = dt_format

    def calculate_sha256(self, file_path):
        if not os.path.exists(file_path):
            return f"FILE_MISSING: {file_path}"
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256().update(byte_block)
            return sha256().hexdigest()
                
# TODO: Create CSV
    def csv_writer(self, action_type, path_before, path_after, file_hash=None):
        file_exists = os.path.isfile(self.log_file)

        with open(self.log_file, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'action_type', 'file_path_before', 'file_path_after', 'hash_before', 'hash_after'])
                f.flush()
                writer.writerow([
                    datetime.now().strftime('%Y%m%d-%H:%M:%S.%f'), 
                    'create_changelog', 
                    None, 
                    os.path.abspath(self.log_file), 
                    None
                    ])
                f.flush()
            
            
# TODO: Create methods for:
# Ingestion
# File Validation
# Metadata Extraction
# Metadata normalisation
# Directory creation/manipulation
# File moving
# BagIt
# Regular Checks

# ERROR REPORTING

# CREATE DATA OBJECT

# INGESTION

# FILE VALIDATION

# METADATA

# ORGANISE

# BAGIT

# Create cronjob or similar to check for corruption on a regular basis.

# CLEANUP AND REPORT
# 


if __name__ == '__main__':
    print(LogWriter("name").calculate_sha256("pypoject.toml"))
