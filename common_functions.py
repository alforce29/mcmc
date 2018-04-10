# -*- coding: utf-8 -*-

def neighbor(data):
    '''
    用于计算方格（i，j）的邻居方格添加到dataframe中
    :param data: DataFrame，
    :return: 增加了neighbor列的DataFrame
    '''
    # data['neighbor'] = data.apply(lambda x: [[x1,y1] for x1 in [x.cell_i-2,x.cell_i-1,x.cell_i,x.cell_i+1,x.cell_i +2] for y1 in [x.cell_j-2, x.cell_j-1, x.cell_j, x.cell_j +1, x.cell_j+2] if (x1 != x.cell_i) or (y1 != x.cell_j)],axis=1)
    data['neighbor'] = data.apply(lambda x: [[x.cell_i - 1, x.cell_j - 1],[x.cell_i - 1, x.cell_j + 1],[x.cell_i - 1, x.cell_j], [x.cell_i, x.cell_j - 1],[x.cell_i, x.cell_j + 1],[x.cell_i + 1, x.cell_j - 1],[x.cell_i +1 , x.cell_j],[x.cell_i + 1, x.cell_j + 1] ],axis=1)
    return data


def neigh(item):
    '''
    用于计算方格（i，j）的邻居方格
    :param item: index
    :return: list
    '''
    neigh_set = [[x1, y1] for x1 in range(item[0]-1, item[0]+2) for y1 in range(item[1]-1, item[1]+2)]

    return neigh_set
