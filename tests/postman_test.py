import subprocess
import pytest
from pathlib import Path

def test_postman_collection():
    collection_path = Path("tests/postman_collection.json")
    result = subprocess.run(
        ["newman", "run", str(collection_path)],
        capture_output=True,
        text=True
    )
    # Newman retorna 0 si todas las pruebas pasan, 1 si falla alguna
    assert result.returncode == 0, f"Newman falló:\n{result.stdout}\n{result.stderr}"