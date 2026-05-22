import os
import time

def generate_evaluation_report(
    documents_output: dict,
    total_elapsed_time: float,
    document_classes: list,
    output_folder: str
) -> None:
    """
    Generates and saves a performance report, including execution times,
    averages, and confusion matrix metrics comparing classifications to ground truths.

    Args:
        documents_output (dict): The output dictionary for all processed documents.
        total_elapsed_time (float): The total execution time of the worker loop.
        document_classes (list): List of configured document class names.
        output_folder (str): Path to the folder where the report should be saved.
    """
    num_docs = len(documents_output)
    if num_docs == 0:
        return

    total_pages = sum(info.get("pages", 0) for info in documents_output.values())
    avg_doc_time = total_elapsed_time / num_docs if num_docs > 0 else 0
    avg_page_time = total_elapsed_time / total_pages if total_pages > 0 else 0

    # Build list of unique classes for the confusion matrix
    ground_truths = []
    predictions = []
    doc_details = []

    for doc_name, info in documents_output.items():
        gt = info.get("ground_truth", "unclassified").lower()
        pred = info.get("classification", "unclassified").lower()
        ground_truths.append(gt)
        predictions.append(pred)
        doc_details.append({
            "name": doc_name,
            "ground_truth": gt,
            "predicted": pred,
            "pages": info.get("pages", 0),
            "time": info.get("time_taken", 0),
            "correct": gt == pred
        })

    # Set of unique classes
    unique_classes = sorted(list(set(document_classes + ground_truths + predictions)))

    # Initialize Confusion Matrix
    # Row: Actual class, Column: Predicted class
    confusion_matrix = {actual: {pred: 0 for pred in unique_classes} for actual in unique_classes}
    for gt, pred in zip(ground_truths, predictions):
        confusion_matrix[gt][pred] += 1

    # Calculate per-class metrics
    class_metrics = {}
    for cls in unique_classes:
        tp = confusion_matrix[cls][cls]
        fp = sum(confusion_matrix[other][cls] for other in unique_classes if other != cls)
        fn = sum(confusion_matrix[cls][other] for other in unique_classes if other != cls)
        
        # True Negatives (TN)
        tn = 0
        for actual in unique_classes:
            if actual != cls:
                for pred in unique_classes:
                    if pred != cls:
                        tn += confusion_matrix[actual][pred]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        class_metrics[cls] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score
        }

    # Overall metrics
    correct_count = sum(1 for d in doc_details if d["correct"])
    accuracy = correct_count / num_docs if num_docs > 0 else 0.0

    macro_precision = sum(metrics["precision"] for metrics in class_metrics.values()) / len(unique_classes) if unique_classes else 0.0
    macro_recall = sum(metrics["recall"] for metrics in class_metrics.values()) / len(unique_classes) if unique_classes else 0.0
    macro_f1 = sum(metrics["f1_score"] for metrics in class_metrics.values()) / len(unique_classes) if unique_classes else 0.0

    # Build Markdown Report
    report_lines = []
    report_lines.append("# Medical Document Processing Evaluation Report")
    report_lines.append(f"\nGenerated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("\n## 1. Executive Summary")
    report_lines.append(f"- **Total Documents Processed:** {num_docs}")
    report_lines.append(f"- **Total Pages Processed:** {total_pages}")
    report_lines.append(f"- **Total Time Taken:** {total_elapsed_time:.2f} seconds")
    report_lines.append(f"- **Overall Accuracy:** {accuracy * 100:.2f}% ({correct_count}/{num_docs})")

    report_lines.append("\n## 2. Timing Metrics")
    report_lines.append("| Metric | Value |")
    report_lines.append("|---|---|")
    report_lines.append(f"| Total Execution Time | {total_elapsed_time:.2f} s |")
    report_lines.append(f"| Average Document Processing Time | {avg_doc_time:.2f} s |")
    report_lines.append(f"| Average Page Processing Time | {avg_page_time:.2f} s |")

    report_lines.append("\n## 3. Individual Document Performance")
    report_lines.append("| Document Name | Pages | Processing Time | Ground Truth | Model Prediction | Correct |")
    report_lines.append("|---|---|---|---|---|---|")
    for doc in doc_details:
        correct_str = "✅ Yes" if doc["correct"] else "❌ No"
        report_lines.append(
            f"| {doc['name']} | {doc['pages']} | {doc['time']:.2f} s | `{doc['ground_truth']}` | `{doc['predicted']}` | {correct_str} |"
        )

    report_lines.append("\n## 4. Confusion Matrix")
    # Header
    matrix_header = "| Actual \\ Predicted | " + " | ".join(f"`{cls}`" for cls in unique_classes) + " |"
    matrix_separator = "|---|" + "|---|".join("" for _ in unique_classes)
    report_lines.append(matrix_header)
    report_lines.append(matrix_separator)
    # Rows
    for actual in unique_classes:
        row_str = f"| `{actual}` | " + " | ".join(str(confusion_matrix[actual][pred]) for pred in unique_classes) + " |"
        report_lines.append(row_str)

    report_lines.append("\n## 5. Per-Class Metrics")
    report_lines.append("| Class | TP | FP | FN | TN | Precision | Recall | F1-Score |")
    report_lines.append("|---|---|---|---|---|---|---|---|")
    for cls in unique_classes:
        metrics = class_metrics[cls]
        report_lines.append(
            f"| `{cls}` | {metrics['tp']} | {metrics['fp']} | {metrics['fn']} | {metrics['tn']} | "
            f"{metrics['precision'] * 100:.2f}% | {metrics['recall'] * 100:.2f}% | {metrics['f1_score'] * 100:.2f}% |"
        )

    report_lines.append("\n## 6. Global Model Performance")
    report_lines.append("| Metric | Value |")
    report_lines.append("|---|---|")
    report_lines.append(f"| Accuracy | {accuracy * 100:.2f}% |")
    report_lines.append(f"| Macro Precision | {macro_precision * 100:.2f}% |")
    report_lines.append(f"| Macro Recall | {macro_recall * 100:.2f}% |")
    report_lines.append(f"| Macro F1-Score | {macro_f1 * 100:.2f}% |")

    report_content = "\n".join(report_lines)

    # Ensure output folder exists and write report
    if output_folder:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        report_path = os.path.join(output_folder, "performance_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"\n[EVALUATION] Performance report saved successfully to: {report_path}\n")
    else:
        print("\n[EVALUATION] Warning: Output folder is not configured. Report not saved to file.\n")
        print(report_content)
