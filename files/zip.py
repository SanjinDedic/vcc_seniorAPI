import zipfile

def count_text_files_in_zip(zip_name='archive.zip'):
    total_text_files = 0
    non_empty_text_files = 0

    with zipfile.ZipFile(zip_name, 'r') as zip_ref:
        # Get a list of all files in the zip
        all_files = zip_ref.namelist()

        # Filter out text files
        text_files = [f for f in all_files if f.endswith('.txt')]
        total_text_files = len(text_files)

        # Check for non-empty text files
        for file in text_files:
            with zip_ref.open(file) as f:
                content = f.read()
                if content:  # Non-empty if content is not empty
                    non_empty_text_files += 1

    print(f'Total text files: {total_text_files}')
    print(f'Non-empty text files: {non_empty_text_files}')

if __name__ == '__main__':
    count_text_files_in_zip()