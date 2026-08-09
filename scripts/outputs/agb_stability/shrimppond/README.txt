# Clark zips in this folder

Brazil and Nicaragua were fetched from the official Clark CGA S3 mirrors:

- `brazil_landcover_change_maps_1999_2014_2018_2020_2022.zip` (~319 MB)
- `nicaragua_landcover_change_maps_1999_2014_2018_2020_2022.zip` (~38 MB)

## Copy into your OneDrive folder

On your PC, either copy these two files into:

```text
C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond
```

or run (downloads only if missing):

```powershell
cd <repo>\scripts\remnant_mangrove_shrimppond
python fetch_missing_clark.py --only brazil nicaragua `
  --clark-dir "C:\Users\Md Mizanur Rahman\OneDrive\Desktop\scripts\outputs\agb_stability\shrimppond"
```
