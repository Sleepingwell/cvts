import pandas as pd
import numpy as np
import glob
from sklearn.cluster import dbscan

KMS_PER_RADIAN = 6371.0088
EPSILON        = 0.02/KMS_PER_RADIAN

def calculate_base(lons, lats, speeds):
    df = pd.DataFrame({'lon': lons, 'lat': lats})[np.array(speeds) <= 1]
    coords = df[['lon', 'lat']].to_numpy()

    _, df["cluster"] = dbscan(
        coords,
        eps=EPSILON,
        min_samples=len(df)/20,
        algorithm='ball_tree',
        metric='haversine')

    # Group clusters
    clust = df.groupby(df.cluster).agg({
        'lon': ['mean'],
        'lat': ['mean', 'size']
        }).droplevel(axis=1, level=0).reset_index().sort_values(by='size',
                ascending=False)
    clust.columns = ['cluster', 'lon', 'lat', 'size']

    # remove unclustered
    clust = clust[clust.cluster != -1]
    if(clust.shape[0] > 0):
        base = clust[:1]
        return float(base['lon']), float(base['lat'])

    return None
