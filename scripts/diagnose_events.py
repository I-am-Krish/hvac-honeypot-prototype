import pandas as pd
import sys
import os
p = os.path.join(os.path.dirname(__file__), '..', 'logs', 'events.csv')
try:
    df = pd.read_csv(p)
except Exception as e:
    print('read_csv error:', e)
    sys.exit(1)
print('rows, cols:', df.shape)
null_ts = df['ts'].isnull().sum()
print('null ts count:', null_ts)
if null_ts>0:
    print(df[df['ts'].isnull()].head(20).to_csv(index=False))
else:
    # find non-integer-like ts
    bad = df[~df['ts'].astype(str).str.match(r'^\d+$')]
    print('non-integer-like ts rows:', len(bad))
    if len(bad)>0:
        print(bad.head(20).to_csv(index=False))
print('sample dtypes:')
print(df.dtypes)
