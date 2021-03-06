
# coding=utf-8
# 20180425
import numpy as np
import pandas as pd
from scipy.stats import rv_discrete
from munch import Munch
import yaml 
import os
import inspect
from auto import operators_expr
from datetime import datetime


def select_from_prob(dist_name, prob_dict):
    # prob_dict {param:probability}  e.g.{20:0.5}
    # 参数的概率加起来必须等于1
    # if np.sum(prob_dict.values()) == 1.: 
    #   pass
    # else:
    #   raise Exception('%s param sum should be 1' %dist_name)
    a = range(len(prob_dict))
    b = list(prob_dict.values())
    return rv_discrete(values=(a, b))



class ExprGenerator():
    def __init__(self):
        self._load_prob_yaml()
        self._init_element()
        self._init_operators_expr()
        self._init_engine()
        self._init_operators_blacklist()

    # --------------------------------------------------------------------
    def _init_operators_blacklist(self):
        yaml_path = os.path.join(os.path.dirname(__file__),'operators_blacklist.yaml')
        with open(yaml_path, 'r') as ff:
            self.operators_blacklist = yaml.load(ff) 


    # --------------------------------------------------------------------
    def _load_prob_yaml(self):
        yaml_path = os.path.join(os.path.dirname(__file__),'prob_control.yaml')
        with open(yaml_path, 'r') as ff:
            self.prob_yaml = yaml.load(ff)


    # --------------------------------------------------------------------
    def _init_element(self):
        self.elements_dict = {}
        for i in self.prob_yaml['elements']:
            self.elements_dict[i] = self.prob_yaml['elements'][i]['probability']
        self.elements_list = list(self.elements_dict.keys())

        if 'e' in self.elements_dict.values():
            for i in self.elements_dict:
                self.elements_dict[i] = 1./len(self.elements_dict)
        self.elements_info = pd.DataFrame(self.elements_dict, index=['probability']).T


    # --------------------------------------------------------------------
    def _init_operators_expr(self):
        self.operators_dict = {}
        for i in self.prob_yaml['operators']:
            self.operators_dict[i] = self.prob_yaml['operators'][i]['probability']
        self.operators_list = list(self.operators_dict.keys())

        if 'e' in self.operators_dict.values():
            for i in self.operators_dict:
                self.operators_dict[i] = 1./len(self.operators_dict)
        self.operators_info = pd.DataFrame(self.operators_dict, index=['probability']).T



    # --------------------------------------------------------------------
    def _init_engine(self):
        self.elements_engine = select_from_prob('elements', self.elements_dict)
        self.operators_engine = select_from_prob('operators', self.operators_dict)


        self.params_info = []
        self.params_engine, self.params_dict = Munch(), Munch()
        for i in self.prob_yaml['operators']:
            self.params_engine[i], self.params_dict[i] = Munch(), Munch()
            for j in self.prob_yaml['operators'][i]:
                if 'probability' in j: continue
                self.params_dict[i][j] = self.prob_yaml['operators'][i][j]
                self.params_engine[i][j] = select_from_prob('%s.%s' %(i, j), self.params_dict[i][j])
                self.params_info.append('%s.%s %s' %(i, j, self.params_dict[i]))



    def gen_param(self, operator_names, param_name):
        # 产生指定运算符的指定参数名的参数值
        param_list = list(self.params_dict[operator_names][param_name].keys())
        return param_list[self.params_engine[operator_names][param_name].rvs()]


    # =====================================================================
    # 外部调用
    def get_one_element(self):
        # 获取一个元素（OHLCV中的一个）
        return self.elements_list[self.elements_engine.rvs()]


    def get_one_operator(self):
        # 获取一个运算符
        return self.operators_list[self.operators_engine.rvs()]



    # --------------------------------------------------------------------
    def get_elements_info(self):
        # 获取元素的概率表
        return self.elements_info

    def get_operators_info(self):
        # 获取运算符的概率表
        return self.operators_info

    def get_params_info(self):
        # 获取运算符的参数的概率表
        return self.params_info


    # --------------------------------------------------------------------
    def _get_one_expr_str(self, layer_num):
        layer_num = int(layer_num)
        if layer_num == 0:
            return self.get_one_element()
        else:
            while True:
                #print('layer:%s' %layer_num)
                op = self.get_one_operator()
                args_list = []
                op_arg = inspect.getargspec(getattr(operators_expr, op))
                for i in range(len(op_arg.args)):
                    args_list.append(self._get_one_expr_str(layer_num-1))
                layer_num -= 1
                return getattr(operators_expr, op)(*args_list)

    
    def _expr_blacklist_check(self, expr_str):
        for i in self.operators_blacklist['blacklist']:
            if i in expr_str:
                print('[ExprGenerator] Blacklist rules blocked this expr_str: %s' %(expr_str))
                return None
        return expr_str
    
    def get_one_expr(self, layer_num):
        expr_str = self._get_one_expr_str(layer_num)
        if self._expr_blacklist_check(expr_str) is None: return None
        expr = {
            "expr": expr_str,
            "layer": layer_num,
            "create_date": str(datetime.now())[:19],
            "backtest": "Undo"
        }
        print('[ExprGenerator] layer:%s expr:%s' %(expr['layer'], expr['expr']))
        return expr





