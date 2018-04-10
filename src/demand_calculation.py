# -*- coding: utf-8 -*-
import pandas as pd
import pickle
from configuration import *
from common_functions import neigh


def demand_transformation(score_dict, sta, result, result_path):
    '''
    计算每个候选点的需求打分函数
    :param score_dict: 每个候选点的需求的总评分，dictionary
    :param sta: stationdata,包含了所有现实的信息，DataFrame
    :param result_path: 存储结果的路径
    :return: 模型会把打分结果存成csv保存在指定路径下
    '''

    score_list = []
    for item in score_dict:
        temp = []
        temp.append(item[0])  # 第i行
        temp.append(item[1])  # 第j列
        if sta[(sta['cell_i'] == item[0]) & (sta['cell_j'] == item[1])]['cnt'].tolist()[0] > 0:
            temp.append('Current')  # 输入点的type 现有点还是候选点
        else:
            temp.append('Candidate')
        temp.append(score_dict[item])  # 输出总评分
        if item in result['x_sol']:
            if result['x_sol'][item] > 0.5:
                temp.append(int(score_dict[item] * 1.0 / result['x_sol'][item]))  # 计算每个枪的评分
            else:
                temp.append(0)

        score_list.append(temp)

    score_table = pd.DataFrame(score_list, columns=['cell_i', 'cell_j', 'type', 'total score', 'average score'])
    score_table = score_table.sort_values(by="average score", ascending=False)
    score_table = score_table.reindex()
    score_table.to_csv(result_path + 'score_table.csv')
    with open(result_path + 'score_table.pkl', 'wb') as fout:
        pickle.dump(score_table, fout)


def demand_calculation(data, sta):
    score = {}
    for i in range(len(sta)):
        score[sta.iloc[i]['cell_i'], sta.iloc[i]['cell_j']] = 0  # 初始化分数的dictionary

    for item in data['a_sol']:
        for temp in neigh(item):
            if (temp[0], temp[1]) in data['x_sol']:  # 累计分数到每个点上
                score[temp[0], temp[1]] += data['x_sol'][temp[0], temp[1]] * 1.0 * data['a_sol'][item] / sum(
                    data['x_sol'][thing[0], thing[1]] for thing in neigh(item) if (thing[0], thing[1]) in data['x_sol'])
    return score
