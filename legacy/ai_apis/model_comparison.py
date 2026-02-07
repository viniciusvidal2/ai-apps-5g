import os
import sys
import time
import json
from typing import List, Dict

# Ensure we can import from the same directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from ai_assistant import AiAssistant

def compare_models():
    # Configuration
    embedding_model_name = "qwen3-embedding:0.6b"
    models_to_test = [
        "gemma3:27b",
        "nemotron-3-nano:30b",
        "glm-4.7-flash:q8_0"
    ]
    
    # Define test cases
    test_cases = [
        {
            "url": "https://pt.wikipedia.org/wiki/Constitui%C3%A7%C3%A3o_brasileira_de_1988",
            "query": "Quais são os fundamentos da República Federativa do Brasil?"
        },
        {
            "url": "https://royalsociety.org/-/media/Royal_Society_Content/policy/projects/climate-evidence-causes/climate-change-evidence-causes.pdf",
            "query": "What are the main lines of evidence that humans are causing climate change?"
        }
    ]

    results_file = "model_comparison_results.md"
    
    print("Initializing AI Assistant...")
    # Initialize with the first model
    ai_assistant = AiAssistant(
        embedding_model_name=embedding_model_name,
        inference_model_name=models_to_test[0],
        documents_db_path="./dbs/chroma_documents_db_comparison",
        collection_name="comparison_collection"
    )

    all_results = []

    try:
        for model_name in models_to_test:
            print(f"\n\nTesting model: {model_name}")
            ai_assistant.switch_assistant_model(model_name)
            
            model_results = {
                "model": model_name,
                "answers": []
            }

            for case in test_cases:
                url = case["url"]
                query = case["query"]
                
                print(f"  Processing query: {query}")
                # print(f"  Source: {url}") # Source ignored for basic test

                try:
                    # Extended "basic" prompt
                    prompt = f"""Answer the following question.
                    
QUESTION:
{query}

ANSWER:"""
                    
                    # 3. excessive inference
                    start_inference = time.time()
                    response = ai_assistant.llm.invoke(prompt).content
                    end_inference = time.time()
                    inference_time = end_inference - start_inference
                    print(f"  Inference took: {inference_time:.2f}s")

                    model_results["answers"].append({
                        "query": query,
                        "url": url, # Keeping url in result for reference
                        "answer": response,
                        "time_taken": inference_time
                    })

                except Exception as e:
                    print(f"  Error processing case: {e}")
                    model_results["answers"].append({
                        "query": query,
                        "url": url,
                        "answer": f"ERROR: {str(e)}",
                        "time_taken": 0
                    })
            
            all_results.append(model_results)

    finally:
        ai_assistant.close_assistant()

    # Write results to file
    with open(results_file, "w") as f:
        f.write("# Model Comparison Results\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for res in all_results:
            model = res["model"]
            f.write(f"## Model: {model}\n\n")
            for ans in res["answers"]:
                f.write(f"### Query: {ans['query']}\n")
                f.write(f"**Source**: {ans['url']}\n\n")
                f.write(f"**Time Taken**: {ans['time_taken']:.2f}s\n\n")
                f.write(f"**Answer**:\n{ans['answer']}\n\n")
                f.write("---\n\n")

    print(f"\nResults written to {results_file}")

if __name__ == "__main__":
    compare_models()
