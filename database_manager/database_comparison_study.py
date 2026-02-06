import chromadb
from rich.console import Console
from rich.table import Table

# Initialize Rich console for pretty printing
console = Console()


def get_db_results(db_path: str, collection_name: str, queries: list[str], n_results: int = 2) -> list[dict]:
    """
    Gets the results for the specific database from the given queries

    Args:
        db_path (str): _path to the database
        collection_name (str): _name of the collection
        queries (list[str]): _list of queries to run
        n_results (int, optional): _number of results to return. Defaults to 2.

    Returns:
        list[dict]: _list of results for each query
    """
    # Initialize Client
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(name=collection_name)

    all_results = []
    for q in queries:
        res = collection.query(query_texts=[q], n_results=n_results)
        # Store query results associated with the question
        all_results.append({
            "question": q,
            "docs": res['documents'][0],
            "distances": res['distances'][0]
        })
    return all_results


def run_benchmark() -> None:
    """Runs the benchmark comparison between two database setups."""
    questions = [
        "Quais são os compromissos da Santo Antônio Energia em relação à saúde, segurança e meio ambiente?",
        "Como a Santo Antônio Energia promove a participação das partes interessadas no Sistema de Gestão Integrada?",
        "Quais são os principais critérios para que a Área de TI da Santo Antônio Energia defina o nível de apoio aos sistemas?",
        "O que acontece quando um fornecedor obtém um IDF inferior a 70?",
        "Quais são os limites de reembolso para refeições durante viagens corporativas?"
    ]

    # Define your two setups
    configs = [
        {"name": "BGE-M3 DB", "path": "./chroma_db"},
        {"name": "Qwen-8B DB", "path": "./chroma_qwen8"}
    ]

    # Fetch results for both
    results_a = get_db_results(configs[0]['path'], "my_collection", questions)
    results_b = get_db_results(configs[1]['path'], "my_collection", questions)

    # 3. Print the Comparison Table
    for i in range(len(questions)):
        table = Table(title=f"Question {i+1}: {questions[i]}", show_lines=True)
        table.add_column("Source DB", style="cyan", no_wrap=True)
        table.add_column("Distance (Lower is Better)", style="magenta")
        table.add_column("Text Preview", style="green")

        # Top result from DB A
        table.add_row(
            configs[0]['name'],
            f"{results_a[i]['distances'][0]:.4f}",
            results_a[i]['docs'][0][:150] + "..."
        )
        # Top result from DB B
        table.add_row(
            configs[1]['name'],
            f"{results_b[i]['distances'][0]:.4f}",
            results_b[i]['docs'][0][:150] + "..."
        )

        console.print(table)
        console.print("\n")


if __name__ == "__main__":
    run_benchmark()
