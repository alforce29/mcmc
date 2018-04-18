import pandas as pd
import pickle

info = pd.read_excel('data/2.xlsx')

with open('data/station_data.pkl','rb') as fin:
    sta = pickle.load(fin)


# for ind in xrange(len(info)):
#     if len(sta[(sta.cell_i == info.iloc[ind]['nlon'])&(sta.cell_j == info.iloc[ind]['nlat'])]) >0 :
#         print sta[(sta.cell_i == info.iloc[ind]['nlon'])&(sta.cell_j == info.iloc[ind]['nlat'])]

for ind in xrange(len(sta)):
    if len(info[(info.nlon == sta.iloc[ind]['cell_i']) & (info.nlat == sta.iloc[ind]['cell_j'])]) == 0:
        print sta.iloc[ind]['cell_i'],sta.iloc[ind]['cell_j'],info[(info.nlon == sta.iloc[ind]['cell_i']) & (info.nlat == sta.iloc[ind]['cell_j'])]

with open('griddata.pkl', 'rb') as fin:
    grid = pickle.load(fin)

info = pd.read_excel('2y.xlsx')
score = pd.read_csv('score_table.csv')
b = pd.merge(info,grid,left_on=['nlon','nlat'],right_on=['cell_i','cell_j'])
a = pd.merge(info,score,left_on =['nlon','nlat'],right_on=['cell_i','cell_j'])
a.to_csv('final6.csv')
b.to_csv('test.csv')