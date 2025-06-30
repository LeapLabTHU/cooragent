from pathlib import Path
from functools import lru_cache
from datetime import datetime
from pathlib import Path
import re
import logging

@lru_cache(maxsize=None)
def get_project_root() -> Path:
    """
    Determine the project root directory by searching for project identification files (e.g., .git, .project-root, etc.)
    Supports multiple strategies to ensure reliability
    """
    # Strategy 1: Search upwards from the current file
    current_path = Path(__file__).parent.absolute()
    max_depth = 10  # Prevent infinite loop
    
    for _ in range(max_depth):
        if (current_path / '.git').exists() or \
           (current_path / 'pyproject.toml').exists() or \
           (current_path / '.project-root').exists():
            return current_path
        current_path = current_path.parent
    
    # Strategy 2: Search upwards from the working directory
    current_path = Path.cwd()
    for _ in range(max_depth):
        if (current_path / '.git').exists():
            return current_path
        current_path = current_path.parent
    
    # Strategy 3: Use installation path
    return Path(__file__).parent.parent.parent


def create_dir_and_file(directory_path, file_name):
    try:
        dir_path = Path(directory_path)    
        dir_path.mkdir(parents=True, exist_ok=True)    
        file_path = dir_path / file_name    
        if not file_path.exists():
            file_path.touch()
    except Exception as e:
        logging.error(f"Exception happens when create file {file_name} in dir {directory_path}")
        raise
        
    


def generate_output_prefix_path(output_summary_dir:str, prefix:dir, suffix:dir='json')->str:
    output_summary_dir = Path(output_summary_dir)
    current_date = datetime.now().strftime("%Y%m%d")
    pattern = re.compile(rf"{prefix}_{current_date}_(\d+).json")
    output_summary_dir.mkdir(parents=True, exist_ok=True)

    existing_files = list(output_summary_dir.glob(f"{prefix}_*_*.{suffix}"))
    max_index = -1
    for file in existing_files:
        match = pattern.match(file.name)
        if match:
            index = int(match.group(1))
            max_index = max(max_index, index)

    new_file_name = f"{prefix}_{current_date}_{max_index + 1}.{suffix}"
    create_dir_and_file(output_summary_dir, new_file_name)
    new_file_path = output_summary_dir / new_file_name
    return new_file_path

def test():
    output_summary_dir = "/mnt/d/code/plato-server/data/test"
    output_summary_path = generate_output_prefix_path(output_summary_dir, prefix='test', suffix='json')
    print(f"New output summary path: {output_summary_path}")
    
