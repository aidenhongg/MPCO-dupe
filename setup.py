import requests
from typing import Dict
import json
import subprocess

def regenerate_contexts(links : dict) -> None:
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

    # open and iterate through the links
    with open('GH_REPOS.json', 'r') as f:
        links = json.load(f)
    
    repo_infos = {repo: get_repo_info(data['owner'], data['name']) for repo, data in links.items()}
    
    with open('./contexts/project_contexts.json', 'w') as f:
        json.dump(repo_infos, f, indent=4)

def regenerate_repos(links : dict) -> None:        
    for repo in links.values():
        owner = repo['owner']
        name = repo['name']

        subprocess.run(['git', 'clone', f"https://github.com/{owner}/{name}.git"],
                       cwd='./profiler/projects',
                       check=True,
                       capture_output=False)

def main():
    with open('GH_REPOS.json', 'r') as f:
        links = json.load(f)

    regenerate_repos(links)
    regenerate_contexts(links)

if __name__ == "__main__":
    main()