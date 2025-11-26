#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status.
set -e

# setup contexts with repositories
python ./setup.py

#make the venv
python3 -m venv ./pipeline/profiler

# activate the venv
source ./pipeline/profiler/bin/activate

# check activation success
echo "Active Python: $(which python)"

# install package managers and test suite
pip install pytest uv

# install local projects to be profiled and edited
uv pip install -e ./pipeline/profiler/projects/langflow
uv pip install -e ./pipeline/profiler/projects/whisper

# deactivate
deactivate

# install remaining dependencies
pip install -r ./requirements.txt

echo "Setup complete"
