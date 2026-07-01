import os
import arkivar
from data_objects import FileState
from utils import create_filestate

def ingest_file(source_path: str)->None:
    data_source = create_filestate(source_path)
    pass 

def ingest_directory(source_path: str)->None:
    # walk tree and add all files to data_sources
    data_sources = []

    for data_source in data_sources:
        pass

def main(source_path: str, destination_path: str):
    if os.path.isfile(source_path):
        ingest_file
        pass
    
