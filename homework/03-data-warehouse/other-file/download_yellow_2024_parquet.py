import os
import requests

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
OUTPUT_DIR = "data/yellow_2024_parquet"

os.makedirs(OUTPUT_DIR, exist_ok=True)

months = range(1, 7)  # Jan–Jun ONLY

for month in months:
    month_str = f"{month:02d}"
    file_name = f"yellow_tripdata_2024-{month_str}.parquet"
    url = f"{BASE_URL}/{file_name}"
    output_path = os.path.join(OUTPUT_DIR, file_name)

    print(f"⬇️ Downloading {file_name}")

    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

    print(f"✅ Saved: {output_path}")

print("\n🎉 All Yellow Taxi Jan–Jun 2024 Parquet files downloaded.")
