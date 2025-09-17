# %%
import pandas as pd
import os
# Function to merge multiple CSV files into one
# %%
dir_path = "./csv_files"
files = os.listdir(dir_path)

# %%

files = [f"{dir_path}/{file}" for file in files if file.endswith('.csv')]

# %%
pd_data = []
for file in files:
    print(file)
    pd_file = pd.read_csv(file)
    pd_file = pd_file.drop_duplicates(subset=['Title'], keep='first')
    pd_data.append(pd_file)
# %%
pd_data_B = pd.concat(pd_data, ignore_index=True, sort=False)
# remove all rows with counts != 3

# %%
# include rows with matched ClaudiaIsRelated and OpenAIIsRelated
pd_data_B = pd_data_B[(pd_data_B['ClaudiaIsRelated'] == pd_data_B['OpenAIIsRelated']) & (pd_data_B['ClaudiaIsRelated'] == True)]
# %%
len(pd_data_B)
# %%
pd_data_C = pd_data_B.groupby('Title').filter(lambda x: len(x) == 3)
# %% remove all rows with counts != 3
pd_data_C = pd_data_C.drop_duplicates(subset=['Title'], keep='first')
# %%
# Save the filtered DataFrame to a new CSV file
pd_data_C.to_csv('merged_output.csv', index=False)
print("Merged CSV file saved as 'merged_output.csv'")