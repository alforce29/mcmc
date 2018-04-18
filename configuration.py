# -*- coding: utf-8 -*-
# FilePath
GridAndStationInfomationPath = 'data/'
StandardResultPath = 'result/standard/'
DepressionAreaResultPath = 'result/Depression_area/'
EvaluationResultPath = 'result/evaluation/'
ScoreResultPath = 'result/score/'



# Parameters of recharging station location part
MaxPileInOneStation = 300
MaxPilePlanToBuild = 3000
StationCost = 1
Theta = 0.01
Rho = 5.0/6
Low = 0.0
IncreasingRatio = 1
MaxSolvingTime = 300
Threshold = 0.5
beta, weight, r = {}, {}, {}
for i in range(0, 24):
    beta[i] = 600
    weight[i] = 1
    r[i] = 1

# Setting Peak Hour
peak_hour = []
for i in peak_hour:
    weight[i] = 1
