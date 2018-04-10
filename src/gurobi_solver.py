# -*- coding: utf-8 -*-
from gurobipy import *
import pickle
import pandas as pd
from configuration import *
from common_functions import neighbor
from common_functions import neigh

def standard_solver(grid_data,station_data,result_path):
    ''' 调用 Gurobi 对标准模型（考虑现实情况）进行求解，候选点集由data中有需求方格产生，现有桩信息从station_data导入（位置，数量）
    station_data也可导入禁止建造的点的位置
    :param grid_data: 从pkl中提取的DataFrame,表头为：cell_i,cell_j,hour,demand,neighbor
    :param station_data:从pkl中提取的DataFrame，表头为：cell_i,cell_j,cnt,其中cnt若为大于0的数字，表示现有桩实际的数量；cnt若为0，
    则表示客户提供的候选点的位置；cnt若为小于0的数字，则表示该方格被禁止建设充电桩
    :param result_path: 存储结果的指定路径
    :return: 模型会将所有的求解结果导入pkl文件，存在相应的path下
    '''
    data = neighbor(grid_data)
    index = xrange(len(data))  # total length of data
    data['demand'] = data.apply(lambda x: 0.0 if x.demand < Threshold else x.demand * IncreasingRatio, axis=1)
    print 'sum:', data['demand'].sum()
    # Declare model
    M = Model('location for station of mcmc')

    # Declare variables
    x, f, g, a, z = {}, {}, {}, {}, {}

    # Declare the decision variable x from location candidates set
    cnt = 0
    tmp = {}
    for ind in range(len(station_data)):
        i = int(station_data.iloc[ind]['cell_i'])
        j = int(station_data.iloc[ind]['cell_j'])
        x[i, j] = M.addVar(vtype=GRB.INTEGER, lb=0, name="x_{}_{}".format(i, j))
        z[i, j] = M.addVar(vtype=GRB.BINARY, lb=0, name="z_{}_{}".format(i, j))
        M.update()

    for ind in index:
        if data.iloc[ind]['demand'] > 0.5:
            i = int(data.iloc[ind]['cell_i'])
            j = int(data.iloc[ind]['cell_j'])
            t = int(data.iloc[ind]['hour'])
            x[i, j] = M.addVar(vtype=GRB.INTEGER, lb=0, name="x_{}_{}".format(i, j))
            z[i, j] = M.addVar(vtype=GRB.BINARY, lb=0, name="z_{}_{}".format(i, j))
            a[i, j, t] = M.addVar(vtype=GRB.CONTINUOUS, lb=0, name="a_{}_{}_{}".format(i, j, t))
            f[i, j, t] = M.addVar(vtype=GRB.CONTINUOUS, lb=0, name="f_{}_{}_{}".format(i, j, t))
            for square in data.iloc[ind]['neighbor']:
                # [k,l] is one of [i,j]'s neighbor
                k = int(square[0])
                l = int(square[1])
                g[i, j, t, k, l] = M.addVar(vtype=GRB.CONTINUOUS, lb=0, name="g_{}_{}_{}_{}".format(i, j, t, k, l))
                g[k, l, t, i, j] = M.addVar(vtype=GRB.CONTINUOUS, lb=0, name="g_{}_{}_{}_{}".format(k, l, t, i, j))

    M.update()
    print 'Variable declaration completed'

    # Declare constraints
    for ind in range(len(station_data)):  # 将现有桩信息和禁止建设信息导入模型的限制条件之中
        i = int(station_data.iloc[ind]['cell_i'])
        j = int(station_data.iloc[ind]['cell_j'])
        if station_data.iloc[ind]['cnt'] > 0 and (i, j) not in tmp:
            tmp[i, j] = 1
            # cnt += station_data.iloc[ind]['cnt']
            # print cnt, station_data.iloc[ind]['cnt'], (i, j)
            M.addConstr(x[i, j] == int(station_data.iloc[ind]['cnt']))
        elif station_data.iloc[ind]['cnt'] < 0 and (i, j) not in tmp:
            tmp[i, j] = 1
            M.addConstr(x[i, j] == 0)
            M.update()

    for ind in index:  # 详见模型 word 说明文档
        if data.iloc[ind]['demand'] > 0.5:
            i = int(data.iloc[ind]['cell_i'])
            j = int(data.iloc[ind]['cell_j'])
            t = int(data.iloc[ind]['hour'])

            M.addConstr(a[i, j, t] == r[t] * (
                    f[i, j, t] + Rho * quicksum(g[int(item[0]), int(item[1]), t, i, j] for item in data.iloc[ind]['neighbor'])))

            if (i, j) not in x:
                M.addConstr(f[i, j, t] == 0)
            else:
                M.addConstr(
            f[i, j, t] + quicksum(g[i, j, t, item[0], item[1]] for item in data.iloc[ind]['neighbor']) <= beta[t] * x[
                i, j])

            M.addConstr(a[i, j, t] <= data.iloc[ind]['demand'])
            M.addConstr(a[i, j, t] >= data.iloc[ind]['demand'] * Low)

    g_neigh = {}
    for item in g:
        g_neigh[item[0], item[1], item[2]] = []

    for item in g:
        if (item[0], item[1]) not in x:
            M.addConstr(g[item] == 0)

    for item in g:
        if [item[3],item[4]] in neigh(item):
            g_neigh[item[0],item[1],item[2]].append(item)

    for ind in g_neigh:
        if len(g_neigh[ind])>0:
            if (ind[0],ind[1]) in x:
                M.addConstr(quicksum(g[item] for item in g_neigh[ind]) <= beta[ind[2]] * x[ind[0],ind[1]])

    for item in x:
        M.addConstr(MaxPileInOneStation * z[item] >= x[item])

    M.addConstr(quicksum(x[item] for item in x) <= MaxPilePlanToBuild)

    M.update()
    # Declare objective function
    M.setObjective(quicksum(weight[item[2]] * a[item] for item in a) - Theta * quicksum(x[item] for item in x)
                   - StationCost * quicksum(z[item] for item in x), GRB.MAXIMIZE)

    # Solve the model declared
    M.setParam(GRB.param.TimeLimit, MaxSolvingTime)
    M.optimize()

    # Export data and save them to pkl files
    x_sol = {}
    a_sol = {}
    f_sol = {}
    g_sol = {}
    for ind in index:
        i = int(data.iloc[ind]['cell_i'])
        j = int(data.iloc[ind]['cell_j'])
        t = int(data.iloc[ind]['hour'])
        if data.iloc[ind]['demand'] > 0.5:
            if abs(a[i, j, t].x - data.iloc[ind]['demand']) > 0.1:
                print 'i:', i, 'j:', j, 't:', t, ':', a[i, j, t].x, data.iloc[ind]['demand']
            a_sol[i, j, t] = a[i, j, t].x

    sol = {}
    cnt1 = 0
    for item in x:
        if x[item].x > 0.5:

            cnt1 += x[item].x

            if len(station_data[(station_data.cell_i == item[0])&(station_data.cell_j == item[1])]['cnt']) <=0:
                x_sol[item] = x[item].x
            elif station_data[(station_data.cell_i == item[0])&(station_data.cell_j == item[1])]['cnt'].tolist()[0] == 0:
                x_sol[item] = x[item].x

    for item in g:
        if g[item].x > 0.001:
            g_sol[item] = g[item].x

    for item in f:
        if f[item].x > 0.001:
            f_sol[item] = f[item].x

    # for item in x:
    #     if station_data[(station_data.cell_i == item[0]) & (station_data.cell_j == item[1])]['cnt'].tolist()[0] == 0:
    #         # if abs(x[item].x - station_data[(station_data.cell_i == item[0])&(station_data.cell_j == item[1])]['cnt'].tolist()[0]) > 0:
    #         print item, x[item].x, station_data[(station_data.cell_i == item[0])&(station_data.cell_j == item[1])]['cnt'].tolist()[0]

    sol['x_sol'] = x_sol
    sol['a_sol'] = a_sol
    sol['g_sol'] = g_sol
    sol['f_sol'] = f_sol
    print 'Total recharging demand satisfied:', sum(a[item].x for item in a)

    sol_list = []
    for item in sol['x_sol']:
        sol_list.append([item[0], item[1], sol['x_sol'][item]])

    sol['sol_list'] = sol_list
    with open(result_path + 'standard_solution.pkl', 'wb') as fout:
        pickle.dump(sol, fout)

    print 'Total piles need to be constructed:', sum(sol['x_sol'][item] for item in sol['x_sol'])
    return 0





def evaluation_solver(data,station_data,result_path):
    ''' 调用 Gurobi 对（考虑现实情况）进行对客户提供的候选点进行打分的前序步骤，将现有桩信息从station_data导入（位置，数量）
    :param data: 从pkl中提取的DataFrame,表头为：cell_i,cell_j,hour,demand,neighbor
    :param station_data:从pkl中提取的DataFrame，表头为：cell_i,cell_j,cnt,其中cnt若为大于0的数字，表示现有桩实际的数量；cnt若为0，
    则表示客户提供的候选点的位置；
    :param result_path: 存储结果的指定路径
    :return: 模型会将所有的求解结果导入pkl文件，存在相应的path下
    '''
    data = neighbor(data)
    data['demand'] = data.apply(lambda x: 0.0 if x.demand < Threshold else x.demand * IncreasingRatio, axis=1)
    index = xrange(len(data))  # total length of data

    # Declare model
    E = Model('location for station of mcmc')

    # Declare variables
    x, f, g, a, z = {}, {}, {}, {}, {}

    # Declare the decision variable x from location candidates set
    cnt = 0
    tmp = {}
    for ind in range(len(station_data)):
        i = station_data.iloc[ind]['cell_i']
        j = station_data.iloc[ind]['cell_j']
        x[i, j] = E.addVar(vtype=GRB.INTEGER, lb=0, name="x_{}_{}".format(i, j))
        z[i, j] = E.addVar(vtype=GRB.BINARY, lb=0, name="z_{}_{}".format(i, j))
        E.update()

    for ind in index:
        if data.iloc[ind]['demand'] > 0.5:
            i = data.iloc[ind]['cell_i']
            j = data.iloc[ind]['cell_j']
            t = data.iloc[ind]['hour']
            a[i, j, t] = E.addVar(vtype=GRB.CONTINUOUS, lb=0, name="a_{}_{}_{}".format(i, j, t))
            f[i, j, t] = E.addVar(vtype=GRB.CONTINUOUS, lb=0, name="f_{}_{}_{}".format(i, j, t))
            for square in data.iloc[ind]['neighbor']:
                # [k,l] is one of [i,j]'s neighbor
                k = square[0]
                l = square[1]
                g[i, j, t, k, l] = E.addVar(vtype=GRB.CONTINUOUS, lb=0, name="g_{}_{}_{}_{}".format(i, j, t, k, l))
                g[k, l, t, i, j] = E.addVar(vtype=GRB.CONTINUOUS, lb=0, name="g_{}_{}_{}_{}".format(k, l, t, i, j))
    print 'Variable declaration completed'
    E.update()

    # Declare constraints

    # 将现有桩信息导入限制条件，如果是客户候选点，则数量为1；如果是已建点，则数量为实际数量
    for ind in range(len(station_data)):
        i = station_data.iloc[ind]['cell_i']
        j = station_data.iloc[ind]['cell_j']
        if station_data.iloc[ind]['cnt'] > 0 and (i, j) not in tmp:
            tmp[i, j] = 1
            # cnt += station_data.iloc[ind]['cnt']
            # print cnt, station_data.iloc[ind]['cnt'], (i, j)
            E.addConstr(x[i, j] == int(station_data.iloc[ind]['cnt']))
        else:
            E.addConstr(x[i, j] == 0)  # 如果给现有桩打分，这里设为0
    print 'Importing reality information completed'

    for ind in index:
        # demand 大于0的方格才进行相应的变量申明，详细constraints解释见word文档
        if data.iloc[ind]['demand'] > 0.5:
            i = data.iloc[ind]['cell_i']
            j = data.iloc[ind]['cell_j']
            t = data.iloc[ind]['hour']
            E.addConstr(a[i, j, t] == r[t] *
                        (f[i, j, t] + Rho * quicksum(g[item[0], item[1], t, i, j]
                                                     for item in data.iloc[ind]['neighbor'])))
            E.addConstr(a[i, j, t] <= data.iloc[ind]['demand'])
            E.addConstr(a[i, j, t] >= data.iloc[ind]['demand'] * Low)
            if (i, j) not in x:  # 如果（i，j)不能建造，自然不存在可供给的电量
                E.addConstr(f[i, j, t] == 0)
            else:
                E.addConstr(f[i, j, t] + quicksum(g[i, j, t, item[0], item[1]] for item in data.iloc[ind]['neighbor'])
                            <= beta[t] * x[i, j])

    for item in g:  # 如果（i，j)不能建造，自然不存在可供给的电量
        if (item[0], item[1]) not in x:
            E.addConstr(g[item] == 0)

    for item in x:
        E.addConstr(MaxPileInOneStation * z[item] >= x[item])

    E.addConstr(quicksum(x[item] for item in x) <= MaxPilePlanToBuild)

    E.update()
    print 'Constraints declaration completed'

    # Declare objective function
    E.setObjective(quicksum(weight[item[2]] * a[item] for item in a) - Theta * quicksum(x[item] for item in x)
                   - StationCost * quicksum(z[item] for item in x), GRB.MAXIMIZE)

    # Solve the model declared
    E.setParam(GRB.param.TimeLimit, MaxSolvingTime)
    E.optimize()

    # Export data and save them to pkl files
    x_sol = {}
    a_sol = {}
    f_sol = {}
    g_sol = {}
    z_sol = {}
    for ind in index:
        i = data.iloc[ind]['cell_i']
        j = data.iloc[ind]['cell_j']
        t = data.iloc[ind]['hour']
        if data.iloc[ind]['demand'] > 0.5:
            if a[i, j, t].x > data.iloc[ind]['demand'] + 0.5:
                print 'i:', i, 'j:', j, 't:', t, ':', a[i, j, t].x, data.iloc[ind]['demand']
            a_sol[i, j, t] = a[i, j, t].x

    sol = {}
    cnt1 = 0
    for item in x:
        if x[item].x > 0.001:
            cnt1 += x[item].x
            x_sol[item] = x[item].x

    for item in g:
        if g[item].x > 0.001:
            g_sol[item] = g[item].x

    for item in f:
        if f[item].x > 0.001:
            f_sol[item] = f[item].x

    for item in z:
        if z[item].x > 0.001:
            z_sol[item] = z[item].x

    sol['z_sol'] = z_sol
    sol['x_sol'] = x_sol
    sol['a_sol'] = a_sol
    sol['g_sol'] = g_sol
    sol['f_sol'] = f_sol
    print 'Total recharging demand satisfied:', sum(a[item].x for item in a)

    sol_list = []
    for item in sol['x_sol']:
        sol_list.append([item[0], item[1], sol['x_sol'][item]])

    sol['sol_list'] = sol_list
    with open(result_path + 'evaluation_solution.pkl', 'wb') as fout:
        pickle.dump(sol, fout)

    print 'Total piles need to be constructed:', sum(sol['x_sol'][item] for item in sol['x_sol'])
    return 0



def unsatisfied_area_calculation_solver(grid_data, station_data, result_path):
    ''' 调用 Gurobi 对（考虑现实情况）进行评估导出充电桩布局洼地，将现有桩信息从station_data导入（位置，数量）
    :param grid_data: 从pkl中提取的DataFrame,表头为：cell_i,cell_j,hour,demand,neighbor
    :param station_data:从pkl中提取的DataFrame，表头为：cell_i,cell_j,cnt,其中cnt若为大于0的数字，表示现有桩实际的数量；cnt若为0，
    则表示客户提供的候选点的位置；
    :param result_path: 存储结果的指定路径
    :return: 模型会将所有的求解结果导入pkl文件，存在相应的path下
    '''
    data = neighbor(grid_data)
    data['demand'] = data.apply(lambda x: 0.0 if x.demand < Threshold else x.demand * IncreasingRatio, axis=1)
    index = xrange(len(data))  # total length of data_table

    # Declare model
    U = Model('location for station of mcmc')

    # Declare variables
    x, f, g, a = {}, {}, {}, {}
    z = {}
    # declare the variable x from location candidates set
    cnt = 0
    tmp = {}
    for ind in range(len(station_data)):
        if station_data.iloc[ind]['cnt'] > 0:
            i = station_data.iloc[ind]['cell_i']
            j = station_data.iloc[ind]['cell_j']
            x[i, j] = U.addVar(vtype=GRB.INTEGER, lb=0, name="x_{}_{}".format(i, j))
            z[i, j] = U.addVar(vtype=GRB.BINARY, lb=0, name="z_{}_{}".format(i, j))
            U.update()

    for ind in range(len(station_data)):
        i = station_data.iloc[ind]['cell_i']
        j = station_data.iloc[ind]['cell_j']
        if station_data.iloc[ind]['cnt'] > 0 and (i, j) not in tmp:
            tmp[i, j] = 1
            cnt += station_data.iloc[ind]['cnt']
            print cnt, station_data.iloc[ind]['cnt'], (i, j)
            U.addConstr(x[i, j] == int(station_data.iloc[ind]['cnt']))
            U.update()

    for ind in index:
        if data.iloc[ind]['demand'] > 0.5:
            i = data.iloc[ind]['cell_i']
            j = data.iloc[ind]['cell_j']
            t = data.iloc[ind]['hour']
            a[i, j, t] = U.addVar(vtype=GRB.CONTINUOUS, lb=0, name="a_{}_{}_{}".format(i, j, t))
            f[i, j, t] = U.addVar(vtype=GRB.CONTINUOUS, lb=0, name="f_{}_{}_{}".format(i, j, t))
            for square in data.iloc[ind]['neighbor']:
                # [k,l] is one of [i,j]'s neighbor
                k = square[0]
                l = square[1]
                g[i, j, t, k, l] = U.addVar(vtype=GRB.CONTINUOUS, lb=0, name="g_{}_{}_{}_{}".format(i, j, t, k, l))
                g[k, l, t, i, j] = U.addVar(vtype=GRB.CONTINUOUS, lb=0, name="g_{}_{}_{}_{}".format(k, l, t, i, j))

    U.update()
    # Declare constraints
    for ind in index:
        if data.iloc[ind]['demand'] > 0.5:
            i = data.iloc[ind]['cell_i']
            j = data.iloc[ind]['cell_j']
            t = data.iloc[ind]['hour']
            U.addConstr(a[i, j, t] <= r[t] * (
                    f[i, j, t] + Rho * quicksum(g[item[0], item[1], t, i, j] for item in data.iloc[ind]['neighbor'])))
            if (i, j) not in x:
                U.addConstr(f[i, j, t] == 0)
            else:
                U.addConstr(
                    f[i, j, t] + quicksum(g[i, j, t, item[0], item[1]] for item in data.iloc[ind]['neighbor']) <= beta[
                        t] * x[
                        i, j])
            U.addConstr(a[i, j, t] <= data.iloc[ind]['demand'])
            U.addConstr(a[i, j, t] >= data.iloc[ind]['demand'] * Low)

    for item in g:
        if (item[0], item[1]) not in x:
            U.addConstr(g[item] == 0)

    for item in x:
        U.addConstr(MaxPileInOneStation * z[item] >= x[item])

    U.addConstr(quicksum(x[item] for item in x) <= MaxPilePlanToBuild)
    U.update()

    # Declare objective function
    U.setObjective(quicksum(weight[item[2]] * a[item] for item in a) - Theta * quicksum(x[item] for item in x)
                   - StationCost * quicksum(z[item] for item in x), GRB.MAXIMIZE)

    # Solve the model declared
    U.setParam(GRB.param.TimeLimit, MaxSolvingTime)
    U.optimize()

    # Export data and save them to pkl files
    depression_list = []
    for ind in index:
        i = data.iloc[ind]['cell_i']
        j = data.iloc[ind]['cell_j']
        t = data.iloc[ind]['hour']
        temp = []
        temp.append(i)
        temp.append(j)
        temp.append(t)
        if data.iloc[ind]['demand'] > 0.5:
            temp.append(data.iloc[ind]['demand'] - a[i, j, t].x)
        else:
            temp.append(data.iloc[ind]['demand'])
        depression_list.append(temp)

    depression_table = pd.DataFrame(depression_list, columns=['cell_i', 'cell_j', 'hour', 'new demand'])

    with open(result_path + 'depression.pkl', 'wb') as fout:
        pickle.dump(depression_table, fout)

    return 0

