import requests
from typing import Dict
import json
import subprocess
import os
import shutil
import platform
from pathlib import Path
import sys
import tomllib
import tomli as tomllib
import re


def regenerate_contexts(repo : str, data : dict) -> None:
    def get_repo_info(owner, repo_name) -> Dict[str, list]:
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json'
            }

            # get description & name
            base = f'https://api.github.com/repos/{owner}/{repo_name}'
            repo_response = requests.get(base, headers=headers)
            repo_response.raise_for_status()
            repo_data = repo_response.json()

            # get languages
            languages_response = requests.get(f'{base}/languages', headers=headers)
            languages_response.raise_for_status()
            languages_data = languages_response.json()

            return {
                'name': repo_data['name'],
                'description': repo_data['description'],
                'languages': ', '.join(list(languages_data.keys()))
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Repo not found: {owner, repo_name}. Please update GH_REPOS.json!")
            elif e.response.status_code == 401:
                raise ValueError("Invalid API key!")
        except Exception as e:
            raise Exception(f"Error getting repo: {e}")
    
    return {repo : get_repo_info(data['owner'], data['name'])}
    
def regenerate_repo(data) -> None:        
    owner = data['owner']
    name = data['name']
    
    base_dir = './pipeline/profiler/projects'
    repo_path = os.path.join(base_dir, name)

    if os.path.isdir(repo_path):
        shutil.rmtree(repo_path)
    
    subprocess.run(['git', 'clone', f"https://github.com/{owner}/{name}.git"],
                   cwd=base_dir,
                   check=True,
                   capture_output=False)

def regenerate_venv(data):
    def run_cmd(cmd, cwd = None):
        str_cmd = [str(arg) for arg in cmd]
        if cwd is None:
            return subprocess.run(str_cmd, check=True, capture_output=False)
        else:
            return subprocess.run(str_cmd, cwd=cwd, check=True, capture_output=False)
    
    name = data['name']
    
    repo_path = Path('./pipeline/profiler/projects').resolve() / name
    venv_path = Path('./pipeline/profiler/venvs').resolve() / f'venv_{name}'
    cache_path = Path('./pipeline/profiler/venvs').resolve() / 'pip_cache'
    
    if platform.system() == "Windows":
        venvpy_path = venv_path / "Scripts" / "python.exe"
    else:
        venvpy_path = venv_path / "bin" / "python"

    # init venv
    if venv_path.exists():
        shutil.rmtree(venv_path)
    run_cmd(['uv', 'venv', venv_path], cwd=repo_path)
    
    # ensure pip 
    run_cmd([venvpy_path, '-m', 'ensurepip', '--upgrade'])
    run_cmd([venvpy_path, '-m', 'pip', 'install', '--upgrade', 'pip', 'setuptools', 'wheel'])

    # dependencies
    run_cmd([venvpy_path, "-m", "pip", "install", '--cache-dir', cache_path, '-e', f"{repo_path}[dev]"])

    # install proj 
    run_cmd([venvpy_path, "-m", "pip", "install", "-e", repo_path])
    
def main():
    with open('GH_REPOS.json', 'r') as f:
        links = json.load(f)
    
    repo_infos = {}
    for repo, data in links.items():
        regenerate_repo(data)
        repo_infos.update(regenerate_contexts(repo, data))
        regenerate_venv(data)

    with open('./contexts/project_contexts.json', 'w') as f:
        json.dump(repo_infos, f, indent=4)

if __name__ == "__main__":
    main()