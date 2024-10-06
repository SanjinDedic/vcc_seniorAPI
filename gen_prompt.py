import os
import re

# Configuration
DOCUMENTATION_FILE = "code_documentation.md"
EXCLUDE_PATTERNS = [
    r"\.pyc$",  # Exclude Python bytecode files
    r"__pycache__",  # Exclude Python cache directories 
    r"\.git",  # Exclude Git directory
    r"\.txt$",  # Exclude text files
    "gen_prompt.py",  # Replace with the name of this script
    "README.md",
    "./apikey.txt",
    "package.json",
    "package-lock.json",
    r"\.DS_Store$",  # Exclude .DS_Store files
    r"\.(jpg|jpeg|png|gif|bmp|ico)$",  # Exclude common image files
    r"\.(pdf|doc|docx|ppt|pptx|xls|xlsx)$",  # Exclude common document files
    r"\.(zip|tar|gz|rar)$",  # Exclude common archive files
]

# Function to generate a Markdown link for a file
def create_markdown_link(filepath, filename):
    relative_path = filepath.replace("\\", "/")  # Normalize path separators
    return f"[{filename}]({relative_path})"

# Function to process a single file
def process_file(filepath):
    # Skip files that match exclude patterns
    if any(re.search(pattern, filepath) for pattern in EXCLUDE_PATTERNS):
        return ''

    try:
        # Try UTF-8 first
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            # If UTF-8 fails, try with ISO-8859-1
            with open(filepath, "r", encoding="iso-8859-1") as f:
                content = f.read()
        except UnicodeDecodeError:
            # If both fail, assume it's a binary file
            return f"### {filepath}\nUnable to read file content. It may be a binary file.\n"
    except Exception as e:
        return f"### {filepath}\nError processing file: {str(e)}\n"
    
    return f"### {filepath}\n```\n{content}\n```\n"

# Main function
def generate_markdown(current_folder_only=False):
    # Delete existing documentation file if it exists
    if os.path.exists(DOCUMENTATION_FILE):
        os.remove(DOCUMENTATION_FILE)
        print(f"Deleted existing {DOCUMENTATION_FILE}")

    markdown_content = "# Project Sitemap\n\n"

    # Determine the starting directory
    start_dir = "." if current_folder_only else os.getcwd()

    for root, dirs, files in os.walk(start_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if not any(re.match(p, d) for p in EXCLUDE_PATTERNS)]
        
        # If current_folder_only is True, don't recurse into subdirectories
        if current_folder_only:
            dirs[:] = []

        if files:
            markdown_content += f"## {root}\n\n"
            for filename in files:
                filepath = os.path.join(root, filename)
                # Only process and add links for files that aren't excluded
                if not any(re.search(pattern, filepath) for pattern in EXCLUDE_PATTERNS):
                    markdown_content += create_markdown_link(filepath, filename) + "\n"
                    markdown_content += process_file(filepath)

    with open(DOCUMENTATION_FILE, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    
    print(f"Generated new {DOCUMENTATION_FILE}")

if __name__ == "__main__":
    # You can change this to True to only document the current folder
    generate_markdown(current_folder_only=True)