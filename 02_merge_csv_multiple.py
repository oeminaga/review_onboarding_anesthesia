
import pandas as pd
import os
import argparse


def main():
    parser = argparse.ArgumentParser(description="Merge multiple CSV files with threshold filtering")
    parser.add_argument('--folder', type=str, default='./csv_files', help='Folder containing CSV files')
    parser.add_argument('--threshold', type=int, default=3, help='Threshold for number of matches to consider')
    parser.add_argument('--match_columns', type=str, nargs='+', default=['ClaudiaIsRelated', 'OpenAIIsRelated'], help='Columns to consider for matching (default: ClaudiaIsRelated OpenAIIsRelated)')
    parser.add_argument('--match_value', type=str, default='True', help='Value to match in all columns (default: True)')
    args = parser.parse_args()

    dir_path = args.folder
    threshold = args.threshold
    match_columns = args.match_columns
    match_value = args.match_value

    files = os.listdir(dir_path)
    files = [f"{dir_path}/{file}" for file in files if file.endswith('.csv')]

    pd_data = []
    for file in files:
        print(file)
        pd_file = pd.read_csv(file)
        pd_file = pd_file.drop_duplicates(subset=['Title'], keep='first')
        pd_data.append(pd_file)

    pd_data_B = pd.concat(pd_data, ignore_index=True, sort=False)

    # include rows where all match_columns equal match_value
    mask = (pd_data_B[match_columns] == match_value).all(axis=1)
    pd_data_B = pd_data_B[mask]

    print(f"Total matched rows: {len(pd_data_B)}")
    # filter by threshold
    pd_data_C = pd_data_B.groupby('Title').filter(lambda x: len(x) == threshold)
    pd_data_C = pd_data_C.drop_duplicates(subset=['Title'], keep='first')

    pd_data_C.to_csv('merged_output.csv', index=False)
    print("Merged CSV file saved as 'merged_output.csv'")

if __name__ == "__main__":
    main()