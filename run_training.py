from data_pipeline.fetch_data import fetch_all_data
from data_pipeline.feature_builder import build_dataset
from models.train_model import train

data = fetch_all_data()
df = build_dataset(data)

print("Dataset built:", df.shape)

train(df)