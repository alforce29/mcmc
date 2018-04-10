# -*- coding: utf-8 -*-
from src.demand_calculation import *
from src.gurobi_solver import *
from configuration import *
import pickle
import os

if __name__ == '__main__':
    # Step 1: Generate unsatisfied demand area
    # Sub-step 1-1: Read gird data
    with open(GridAndStationInfomationPath + 'griddata.pkl', 'rb') as fin:
        grid_data = pickle.load(fin)

    # Sub-step 1-2: Read station data
    with open(GridAndStationInfomationPath + 'stationdata.pkl', 'rb') as fin:
        station_data = pickle.load(fin)
    # Sub-step 1-3: Use calculation_solver to generate pkl file with unsatisfied demand
    if not os.path.exists(DepressionAreaResultPath):
        os.makedirs(DepressionAreaResultPath)
    unsatisfied_area_calculation_solver(grid_data, station_data, DepressionAreaResultPath)

    # Step 2: Evaluation
    # Sub-step 2-1: Read grid data if you skip the step 1
    with open(GridAndStationInfomationPath + 'griddata.pkl', 'rb') as fin:
        grid_data = pickle.load(fin)

    # Sub-step 2-2: Read station data if you skip the step 1
    with open(GridAndStationInfomationPath + 'stationdata.pkl', 'rb') as fin:
        station_data = pickle.load(fin)

    # Sub-Step 2-3: Do the evaluation
    if not os.path.exists(EvaluationResultPath):
        os.makedirs(EvaluationResultPath)
    evaluation_solver(grid_data, station_data, EvaluationResultPath)

    # Step 3: score
    # Sub-step 3-1: Read evaluation result
    with open(EvaluationResultPath + 'evaluation_solution.pkl', 'rb') as fin:
        result = pickle.load(fin)
    # Sub-step 3-2: Read grid data and station data if you skip 1 or 2

    # SUb-step 3-3: Do the scoring
    if not os.path.exists(ScoreResultPath):
        os.makedirs(ScoreResultPath)
    demand_transformation(demand_calculation(result, station_data), station_data, result, ScoreResultPath)

    # Step 4: alternative step if the clients have no recommendation points
    with open(GridAndStationInfomationPath + 'griddata.pkl', 'rb') as fin:
        grid_data = pickle.load(fin)

    with open(GridAndStationInfomationPath + 'stationdata.pkl', 'rb') as fin:
        station_data = pickle.load(fin)

    if not os.path.exists(StandardResultPath):
        os.makedirs(StandardResultPath)
    standard_solver(grid_data, station_data, StandardResultPath)