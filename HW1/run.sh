#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_json_path> <output_json_path>"
    exit 1
fi

# Assign input and output file paths to variables
input_json="$1"
output_json="$2"
rm -f "$output_json"
# Execute the Python script with the provided input and output file paths
python3 main.py "$input_json" "$output_json"
