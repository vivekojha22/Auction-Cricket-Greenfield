import zipfile
import os

filename = "players.xlsx"

print("Exists:", os.path.exists(filename))
print("Size:", os.path.getsize(filename))

print("Is ZIP:", zipfile.is_zipfile(filename))