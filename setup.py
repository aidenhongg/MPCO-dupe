from github import Github, GithubException
from reporoulette import TemporalSampler
import xml.etree.ElementTree as ET
from pathlib import Path

import subprocess
import platform
import tomlkit
import shutil
import json
import stat
import sys
import os
import re

#------------CONSTANTS------------
def _load_key():
    with open('./API_KEYS.json', 'r') as f:
        return json.load(f)['GITHUB_KEY']
GH_KEY = _load_key()
GH_API = Github(GH_KEY)

PROJECTS_DIR = Path('./pipeline/profiler/projects')
VENVS_DIR = Path('./pipeline/profiler/venvs')

#----------REPO MANAGEMENT--------
def regenerate_contexts(author, name) -> dict:    
    repo = GH_API.get_repo(f"{author}/{name}")
    
    return {name: {
        'name': repo.name,
        'description': repo.description,
        'languages': ', '.join(repo.get_languages().keys())
    }}
    
def regenerate_repo(author, name) -> None:
    base_dir = PROJECTS_DIR
    repo_path = base_dir / name

    if os.path.isdir(repo_path):
        shutil.rmtree(repo_path, onexc=_remove_readonly)
    
    _run_cmd(['git', 'clone', f"https://github.com/{author}/{name}.git"], cwd=base_dir)

    toml = repo_path / 'pyproject.toml'
    with open(toml, "r", encoding="utf-8") as f:
        config = tomlkit.load(f)
        ini_options = config.get("tool", {}).get("pytest", {}).get("ini_options", {})
        if not ini_options:
            raise ValueError("No pytest ini_options found in pyproject.toml")

        testpaths = ini_options.get("testpaths", [])
        if isinstance(testpaths, list) and len(testpaths) > 0:
            primary_path = testpaths[0]
            
            if not (repo_path / primary_path).exists():
                raise ValueError(f"Primary testpath '{primary_path}' does not exist in the repository.")

            testpaths.clear()
            testpaths.append(primary_path)

        if platform.system() == "Windows":
            timeout_method = ini_options.get("timeout_method")
            if isinstance(timeout_method, str):
                ini_options["timeout_method"] = "thread"

    with open(toml, "w", encoding="utf-8") as f:
        tomlkit.dump(config, f)

def regenerate_venv(name):
    report_path = Path('.').resolve() / 'report.xml'    
    repo_path = PROJECTS_DIR.resolve() / name

    venv_path = VENVS_DIR.resolve() / f'venv_{name}'
    cache_path = VENVS_DIR.resolve() / 'pip_cache'

    if platform.system() == "Windows":
        venvpy_path = venv_path / "Scripts" / "python.exe"
        activation_cmd = str(venv_path / 'Scripts' / 'activate.bat')

    else:
        venvpy_path = venv_path / "bin" / "python"
        activation_cmd = f'source {venv_path / "bin" / "activate"}'

    install_pip = "&& python -m ensurepip --upgrade && python -m pip install pytest"
    uv_flags = f"&& uv sync --active --project {repo_path} --cache-dir {cache_path}"

    # init venv
    if not os.path.exists(venv_path):
        _run_cmd(['uv', 'venv', venv_path], cwd=repo_path)
    
    # install all dependencies
    _run_cmd(" ".join((activation_cmd, 
            uv_flags,
            "--all-groups",
            install_pip)), shell = True)

    # ensure test works
    result = _run_cmd([venvpy_path, '-m', 'pytest', f"--junitxml={report_path}"], cwd=repo_path, check=False)
    if result.returncode > 1:
        modules = _missing_modules('./pipeline/profiler/temp/result.xml')
        _run_cmd([venvpy_path, '-m', 'pip', 'install', *modules])
        result = _run_cmd([venvpy_path, '-m', 'pytest'], cwd=repo_path, check=False)

        if result.returncode > 1:
            raise RuntimeError(f"Tests failed to run in {name}")

#----------HELPER FUNCTIONS---------
def _run_cmd(cmd, cwd = None, shell = False, check = True):
    str_cmd = [str(arg) for arg in cmd] if not shell else cmd
    return subprocess.run(str_cmd, cwd=cwd, check=check, capture_output=False, shell=shell)

def _setup_projects(author, name, repo_infos):
    regenerate_repo(author, name)
    repo_info = regenerate_contexts(author, name)
    regenerate_venv(name)

    repo_infos.update(repo_info)

def _missing_modules(report):
    tree = ET.parse(report)
    root  = tree.getroot()
    missing_modules = []
    module_pattern = re.compile(r"ModuleNotFoundError: No module named '([^']+)'|ImportError: No module named ([^ \n]+)")

    for testcase in root.iter('testcase'):
        for issue in testcase.findall('error') + testcase.findall('failure'):
            content = issue.text
            if content:
                match = module_pattern.search(content)
                if match:
                    module_name = match.group(1) or match.group(2)
                    missing_modules.append(module_name.split('.')[0])
        
    return missing_modules

def _clean_projects(name : str):
    repo_path = PROJECTS_DIR.resolve() / name
    venv_path = VENVS_DIR.resolve() / f'venv_{name}'
    if os.path.isdir(repo_path):
        shutil.rmtree(repo_path, onexc=_remove_readonly)
    if os.path.isdir(venv_path):
        shutil.rmtree(venv_path, onexc=_remove_readonly)

def _remove_readonly(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

#----------MAIN FUNCTIONS----------
def main():
    with open('GH_REPOS.json', 'r') as f:
        links = json.load(f)
    
    repo_infos = {}
    for data in links.values():
        author, name = data['owner'], data['name'] 
        _setup_projects(author, name, repo_infos)

    with open('./contexts/project_contexts.json', 'w') as f:
        json.dump(repo_infos, f, indent=4)

def sample_main(n=50):
    repo_samples = iter(TemporalSampler(GH_KEY).sample(days_to_sample=5 * n, 
                                                       n_samples=10 * n,
                                                       min_stars = 500, 
                                                       language="python"))
    repo_infos = {}

    while len(repo_infos.keys()) < n:
        try:
            raw_repo = next(repo_samples)
        
        except StopIteration:
            repo_samples = iter(TemporalSampler(GH_KEY).sample(days_to_sample = 5 * n, 
                                                            min_stars = 500,
                                                            n_samples = 10 * n, 
                                                            language="python"))
            continue

        try:
            GH_API.get_repo(raw_repo["full_name"]).get_contents("pyproject.toml")
            match = re.search(r"(?P<author>[^/]+)/(?P<name>.+)", raw_repo["full_name"])
            author, name = match.group("author", "name")
            _setup_projects(author, name, 
                            repo_infos)
        
        except GithubException:
            print("Invalid repo")
            continue

        except Exception:
            _clean_projects(name)
            continue

    with open('./contexts/project_contexts.json', 'w') as f:
        json.dump(repo_infos, f, indent=4)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        if sys.argv[1] == '-s':
            sample_main(n=int(sys.argv[2]))
    else:
        main()

# check pyproject.toml before repo clone