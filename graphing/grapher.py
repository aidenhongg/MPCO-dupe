import pandas as pd
import matplotlib.pyplot as plt

def plot_data(data: pd.DataFrame):
    # Group by prompt_type and calculate mean avg_runtime
    avg_runtime_by_prompt = data.groupby('prompt_type')['runtime_p'].mean().reindex(['MP', 'FS', 'COT', 'BASE'])
    # Mapping for pretty labels
    prompt_type_labels = {
        'MP': 'Metaprompted',
        'FS': 'Few-shot',
        'COT': 'Chain-of-thought',
        'BASE': 'Base context'
    }
    avg_runtime_by_prompt.index = [prompt_type_labels.get(pt, pt) for pt in avg_runtime_by_prompt.index]
   
    # Plot
    plt.figure(figsize=(8, 6))
    avg_runtime_by_prompt.plot(kind='bar', color='skyblue', edgecolor='black')
    plt.xlabel('Prompt Type')
    plt.ylabel('Average % Optimization')
    plt.title('Average % Optimization by Prompt Type')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig('./graphing/graphs/avg_runtime_v_prompt.png')


def plot_avg_runtime_by_optimizer(data: pd.DataFrame):

    optimizers = ['25', '4o', '40']
    optimizer_labels = {
        '25': 'Gemini Pro 2.5',
        '4o': 'OpenAI GPT-4o',
        '40': 'Claude Sonnet 4.0'
    }
    avg_runtime_by_optimizer = data.groupby('optimizer')['runtime_p'].mean().reindex(optimizers)
    avg_runtime_by_optimizer.index = [optimizer_labels.get(opt, opt) for opt in avg_runtime_by_optimizer.index]
    plt.figure(figsize=(8, 6))
    avg_runtime_by_optimizer.plot(kind='bar', color='cornflowerblue', edgecolor='black')
    plt.xlabel('Optimizer')
    plt.ylabel('Average % Optimization')
    plt.title('Average % Optimization by Optimizer')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig('./graphing/graphs/avg_runtime_v_optim.png')

def plot_clustered_bar(data: pd.DataFrame):
    prompt_types = ['MP', 'FS', 'COT', 'BASE']
    optimizers = ['25', '4o', '40']
    prompt_type_labels = {
        'MP': 'Metaprompted',
        'FS': 'Few-shot',
        'COT': 'Chain-of-thought',
        'BASE': 'Base context'
    }
    optimizer_labels = {
        '25': 'Gemini Pro 2.5',
        '4o': 'OpenAI GPT-4o',
        '40': 'Claude Sonnet 4.0'
    }
    # Group by prompt_type and optimizer, then unstack for clustered bar
    grouped = data.groupby(['prompt_type', 'optimizer'])['runtime_p'].mean().unstack('optimizer').reindex(prompt_types)
    grouped = grouped[optimizers]  # Ensure correct optimizer order

    grouped.index = [prompt_type_labels.get(pt, pt) for pt in grouped.index]
    grouped.columns = [optimizer_labels.get(opt, opt) for opt in grouped.columns]
    # Plot
    ax = grouped.plot(kind='bar', figsize=(10, 6), edgecolor='black')
    plt.xlabel('Prompt Type')
    plt.ylabel('Average % Optimization')
    plt.title('Average % Optimization by Prompt Type and Optimizer')
    plt.xticks(rotation=0)
    plt.legend(title='Optimizer')
    plt.tight_layout()
    plt.savefig('./graphing/graphs/avg_runtime_v_prompt_optim.png')

# New functions for failed_attempts
def plot_failed_attempts_by_prompt_type(data: pd.DataFrame):
    prompt_types = ['MP', 'FS', 'COT', 'BASE']
    prompt_type_labels = {
        'MP': 'Metaprompted',
        'FS': 'Few-shot',
        'COT': 'Chain-of-thought',
        'BASE': 'Base context'
    }
    failed_by_prompt = data.groupby('prompt_type')['failed_attempts'].sum().reindex(prompt_types)
    failed_by_prompt.index = [prompt_type_labels.get(pt, pt) for pt in failed_by_prompt.index]
    plt.figure(figsize=(8, 6))
    failed_by_prompt.plot(kind='bar', color='salmon', edgecolor='black')
    plt.xlabel('Prompt Type')
    plt.ylabel('Total Failed Attempts')
    plt.title('Total Failed Attempts by Prompt Type')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig('./graphing/graphs/failed_attempts_v_prompt.png')


def plot_failed_attempts_by_optimizer(data: pd.DataFrame):
    optimizers = ['25', '4o', '40']
    optimizer_labels = {
        '25': 'Gemini Pro 2.5',
        '4o': 'OpenAI GPT-4o',
        '40': 'Claude Sonnet 4.0'
    }
    failed_by_optimizer = data.groupby('optimizer')['failed_attempts'].sum().reindex(optimizers)
    failed_by_optimizer.index = [optimizer_labels.get(opt, opt) for opt in failed_by_optimizer.index]
    plt.figure(figsize=(8, 6))
    failed_by_optimizer.plot(kind='bar', color='lightgreen', edgecolor='black')
    plt.xlabel('Optimizer')
    plt.ylabel('Total Failed Attempts')
    plt.title('Total Failed Attempts by Optimizer')
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig('./graphing/graphs/failed_attempts_v_optim.png')


def plot_failed_attempts_clustered_bar(data: pd.DataFrame):
    prompt_types = ['MP', 'FS', 'COT', 'BASE']
    optimizers = ['25', '4o', '40']
    prompt_type_labels = {
        'MP': 'Metaprompted',
        'FS': 'Few-shot',
        'COT': 'Chain-of-thought',
        'BASE': 'Base context'
    }
    optimizer_labels = {
        '25': 'Gemini Pro 2.5',
        '4o': 'OpenAI GPT-4o',
        '40': 'Claude Sonnet 4.0'
    }
    grouped = data.groupby(['prompt_type', 'optimizer'])['failed_attempts'].sum().unstack('optimizer').reindex(prompt_types)
    grouped = grouped[optimizers]  # Ensure correct optimizer order
    grouped.index = [prompt_type_labels.get(pt, pt) for pt in grouped.index]
    grouped.columns = [optimizer_labels.get(opt, opt) for opt in grouped.columns]
    ax = grouped.plot(kind='bar', figsize=(10, 6), edgecolor='black')
    plt.xlabel('Prompt Type')
    plt.ylabel('Total Failed Attempts')
    plt.title('Total Failed Attempts by Prompt Type and Optimizer')
    plt.xticks(rotation=0)
    plt.legend(title='Optimizer')
    plt.tight_layout()
    plt.savefig('./graphing/graphs/failed_attempts_v_prompt_optim.png')

def graph_main(dataset_file):
    data = pd.read_csv(dataset_file)
    data['runtime_p'] = (data['original_runtimes'] - data['avg_runtime']) / data['original_runtimes'] * 100

    plot_data(data)
    plot_clustered_bar(data)
    plot_failed_attempts_by_prompt_type(data)
    plot_failed_attempts_by_optimizer(data)
    plot_failed_attempts_clustered_bar(data)
    plot_avg_runtime_by_optimizer(data)
