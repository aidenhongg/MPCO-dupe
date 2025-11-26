#!/usr/bin/env bash

set -e

# setup contexts with repositories
python ./setup.py

#make the venv
python3 -m venv ./pipeline/profiler/venv

# activate the venv
source ./pipeline/profiler/venv/bin/activate || exit 1

# check activation success
echo "Active Python: $(which python)"

# install package managers and test suite
pip install pytest uv

# install local projects to be profiled and edited
uv pip install -e ./pipeline/profiler/projects/whisper
pip install anyio orjson asgi-lifespan blockbuster dotenv fastapi httpx numpy scipy
pip install torch --index-url https://download.pytorch.org/whl/cu128

# deactivate
deactivate

# install remaining dependencies
pip install -r ./requirements.txt

echo "Setup complete"
