import os
import sys
import json
import argparse
import yaml

def validate_manifest(file_path, content, index=None):
    errors = []

    # Track which manifest this is (for multi-doc files)
    doc_id = f"{file_path} (doc #{index + 1})" if index is not None else file_path

    if not isinstance(content, dict):
        errors.append({"error": "YAML is not a dictionary object", "file": doc_id})
        return errors

    required_fields = ["apiVersion", "kind", "metadata"]

    for field in required_fields:
        if field not in content:
            errors.append({"error": f"Missing field: {field}", "file": doc_id})

    # Validate metadata.name
    if "metadata" in content and isinstance(content["metadata"], dict):
        if "name" not in content["metadata"]:
            errors.append({"error": "Missing field: metadata.name", "file": doc_id})
    else:
        errors.append({"error": "metadata is not a dictionary", "file": doc_id})

    return errors

def process_directory(directory):
    issues = []
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith((".yaml", ".yml")):
                full_path = os.path.join(root, filename)
                try:
                    with open(full_path, 'r') as f:
                        docs = list(yaml.safe_load_all(f))
                        for idx, doc in enumerate(docs):
                            errors = validate_manifest(full_path, doc, index=idx)
                            issues.extend(errors)
                except Exception as e:
                    issues.append({"error": str(e), "file": full_path})
    return issues

def main():
    parser = argparse.ArgumentParser(description="Kubernetes YAML Validator")
    parser.add_argument("directory", help="Path to directory with YAML files")
    args = parser.parse_args()

    issues = process_directory(args.directory)
    if issues:
        print(json.dumps({"status": "failed", "issues": issues}, indent=2))
        sys.exit(1)
    else:
        print(json.dumps({"status": "success", "message": "All files are valid ✅"}))
        sys.exit(0)

if __name__ == "__main__":
    main()


"""
    How to Use It
    python kube_validate.py ./k8s-manifests/


    Dependencies
    Install PyYAML if not already:
    pip install pyyaml
"""