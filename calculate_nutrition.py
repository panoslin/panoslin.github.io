#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确计算每个菜谱的营养成分
根据食材清单和用量，逐一计算并累加营养成分
"""

import json
import re

# 食材营养成分数据库（每100g或每单位）
# 数据来源：中国食物成分表、USDA等权威营养数据库
# 注意：salt字段表示钠含量（毫克），需要转换为盐含量（克）= 钠含量 / 1000 * 2.54
NUTRITION_DB = {
    # 蛋类
    '鸡蛋': {'calories': 144, 'protein': 13.3, 'carbs': 1.5, 'fat': 8.8, 'salt': 0, 'unit': 'g'},
    '蛋黄': {'calories': 328, 'protein': 15.2, 'carbs': 3.6, 'fat': 28.2, 'salt': 0, 'unit': 'g'},
    # 皮蛋、咸鸭蛋：按常见值近似
    '皮蛋': {'calories': 160, 'protein': 12.8, 'carbs': 4.5, 'fat': 10.0, 'salt': 0, 'unit': 'g'},
    '咸鸭蛋': {'calories': 190, 'protein': 13.0, 'carbs': 3.0, 'fat': 14.5, 'salt': 0, 'unit': 'g'},
    
    # 肉类
    '牛里脊': {'calories': 107, 'protein': 22.2, 'carbs': 0, 'fat': 2.3, 'salt': 0, 'unit': 'g'},
    '牛肉': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '牛腩': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '鸡肉': {'calories': 167, 'protein': 19.3, 'carbs': 0, 'fat': 9.4, 'salt': 0, 'unit': 'g'},
    # 鸡胸肉：脂肪含量更低
    '鸡胸肉': {'calories': 133, 'protein': 19.4, 'carbs': 0, 'fat': 5.0, 'salt': 0, 'unit': 'g'},
    '鸡胸': {'calories': 133, 'protein': 19.4, 'carbs': 0, 'fat': 5.0, 'salt': 0, 'unit': 'g'},
    # 老母鸡：按老母鸡/土鸡近似，略高脂肪和热量
    '老母鸡': {'calories': 200, 'protein': 20.0, 'carbs': 0, 'fat': 12.0, 'salt': 0, 'unit': 'g'},
    '母鸡': {'calories': 200, 'protein': 20.0, 'carbs': 0, 'fat': 12.0, 'salt': 0, 'unit': 'g'},
    # 去骨鸡腿肉：按去皮鸡腿生肉近似，略高脂肪
    '去骨鸡腿肉': {'calories': 180, 'protein': 18.0, 'carbs': 0, 'fat': 12.0, 'salt': 0, 'unit': 'g'},
    # 鸡腿：带骨鸡腿，按去骨鸡腿肉近似（骨头约占30%）
    '鸡腿': {'calories': 180, 'protein': 18.0, 'carbs': 0, 'fat': 12.0, 'salt': 0, 'unit': 'g'},
    '猪肉': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    '猪肝': {'calories': 129, 'protein': 19.3, 'carbs': 5.0, 'fat': 3.5, 'salt': 0, 'unit': 'g'},
    '虾': {'calories': 93, 'protein': 18.6, 'carbs': 2.8, 'fat': 0.8, 'salt': 0, 'unit': 'g'},
    '虾仁': {'calories': 93, 'protein': 18.6, 'carbs': 2.8, 'fat': 0.8, 'salt': 0, 'unit': 'g'},
    # 虾米：干虾米，按常见值
    '虾米': {'calories': 195, 'protein': 43.7, 'carbs': 0, 'fat': 2.6, 'salt': 0, 'unit': 'g'},
    '虾米粒': {'calories': 195, 'protein': 43.7, 'carbs': 0, 'fat': 2.6, 'salt': 0, 'unit': 'g'},
    # 章鱼/八爪鱼：按常见值
    '章鱼': {'calories': 135, 'protein': 18.9, 'carbs': 0, 'fat': 5.0, 'salt': 0, 'unit': 'g'},
    '八爪鱼': {'calories': 135, 'protein': 18.9, 'carbs': 0, 'fat': 5.0, 'salt': 0, 'unit': 'g'},
    # 贝类/螺类（常见值，按每100g可食部分估算）
    # 参考：USDA/中国食物成分表中同类贝类（螺/海螺/田螺）营养范围
    '花螺': {'calories': 110, 'protein': 20.0, 'carbs': 3.0, 'fat': 1.5, 'salt': 0, 'unit': 'g'},
    '旺螺': {'calories': 110, 'protein': 20.0, 'carbs': 3.0, 'fat': 1.5, 'salt': 0, 'unit': 'g'},
    # 生蚝：按常见贝类近似
    '生蚝': {'calories': 57, 'protein': 10.9, 'carbs': 4.7, 'fat': 1.1, 'salt': 0, 'unit': 'g'},
    '蚝': {'calories': 57, 'protein': 10.9, 'carbs': 4.7, 'fat': 1.1, 'salt': 0, 'unit': 'g'},
    # 鲈鱼：按常见海鱼近似
    '鲈鱼': {'calories': 105, 'protein': 18.6, 'carbs': 0, 'fat': 3.4, 'salt': 0, 'unit': 'g'},
    
    # 蔬菜类（天然含钠量很少）
    '番茄': {'calories': 18, 'protein': 0.9, 'carbs': 3.5, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '西红柿': {'calories': 18, 'protein': 0.9, 'carbs': 3.5, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '西兰花': {'calories': 34, 'protein': 2.8, 'carbs': 6.6, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '西蓝花': {'calories': 34, 'protein': 2.8, 'carbs': 6.6, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '茄子': {'calories': 25, 'protein': 1.1, 'carbs': 5.4, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '黄瓜': {'calories': 16, 'protein': 0.7, 'carbs': 3.6, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '白菜': {'calories': 16, 'protein': 1.5, 'carbs': 3.2, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 娃娃菜：按小棵大白菜近似
    '娃娃菜': {'calories': 15, 'protein': 1.3, 'carbs': 2.8, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '青菜': {'calories': 15, 'protein': 1.5, 'carbs': 2.4, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '胡萝卜': {'calories': 41, 'protein': 0.9, 'carbs': 9.6, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    # 白萝卜：按常见值
    '白萝卜': {'calories': 16, 'protein': 0.7, 'carbs': 3.5, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '萝卜': {'calories': 16, 'protein': 0.7, 'carbs': 3.5, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 节瓜/毛瓜：按节瓜/毛瓜近似（类似冬瓜但更小）
    '节瓜': {'calories': 13, 'protein': 0.6, 'carbs': 2.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '毛瓜': {'calories': 13, 'protein': 0.6, 'carbs': 2.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '洋葱': {'calories': 40, 'protein': 1.1, 'carbs': 9.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '大葱': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '小葱': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '香葱': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    # 蒜苗：按蒜苗/蒜薹近似
    '蒜苗': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '蒜薹': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    # 干葱 / 红葱头：按常见小洋葱近似
    '干葱': {'calories': 40, 'protein': 1.4, 'carbs': 9.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '红葱头': {'calories': 40, 'protein': 1.4, 'carbs': 9.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '葱': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '葱花': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '孜然粉': {'calories': 375, 'protein': 22.8, 'carbs': 33.7, 'fat': 22.3, 'salt': 0, 'unit': 'g'},
    '孜然': {'calories': 375, 'protein': 22.8, 'carbs': 33.7, 'fat': 22.3, 'salt': 0, 'unit': 'g'},
    '葱节': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '蒜': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '大蒜': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '蒜头': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '蒜蓉': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '蒜末': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '蒜粒': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '姜': {'calories': 80, 'protein': 1.8, 'carbs': 17.8, 'fat': 0.8, 'salt': 0, 'unit': 'g'},
    '姜片': {'calories': 80, 'protein': 1.8, 'carbs': 17.8, 'fat': 0.8, 'salt': 0, 'unit': 'g'},
    '紫菜': {'calories': 207, 'protein': 28.2, 'carbs': 44.1, 'fat': 1.1, 'salt': 0, 'unit': 'g'},
    # 海带/裙带菜：按泡发后的湿海带近似（干海带泡发后重量约增加10倍）
    '海带': {'calories': 13, 'protein': 1.2, 'carbs': 2.1, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '裙带菜': {'calories': 13, 'protein': 1.2, 'carbs': 2.1, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '香菜': {'calories': 23, 'protein': 2.1, 'carbs': 3.7, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '小米辣': {'calories': 40, 'protein': 1.9, 'carbs': 8.8, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '小米椒': {'calories': 40, 'protein': 1.9, 'carbs': 8.8, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '青红小米辣': {'calories': 40, 'protein': 1.9, 'carbs': 8.8, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '羽衣甘蓝': {'calories': 49, 'protein': 4.3, 'carbs': 8.8, 'fat': 0.9, 'salt': 0, 'unit': 'g'},
    '小卷心菜': {'calories': 25, 'protein': 1.3, 'carbs': 5.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '金针菇': {'calories': 32, 'protein': 2.4, 'carbs': 6.0, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    # 包菜：卷心菜
    '包菜': {'calories': 25, 'protein': 1.3, 'carbs': 5.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '卷心菜': {'calories': 25, 'protein': 1.3, 'carbs': 5.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 荷兰豆/豌豆：按雪豆/甜豆近似
    '荷兰豆': {'calories': 31, 'protein': 2.5, 'carbs': 5.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '豌豆': {'calories': 31, 'protein': 2.5, 'carbs': 5.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    # 木耳：按黑木耳/云耳近似（泡发后）
    '木耳': {'calories': 21, 'protein': 1.5, 'carbs': 6.0, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '黑木耳': {'calories': 21, 'protein': 1.5, 'carbs': 6.0, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    
    # 主食类
    '面饼': {'calories': 280, 'protein': 9.0, 'carbs': 58.0, 'fat': 1.0, 'salt': 0, 'unit': 'g'},
    '面条': {'calories': 280, 'protein': 9.0, 'carbs': 58.0, 'fat': 1.0, 'salt': 0, 'unit': 'g'},
    # 粉丝/龙口粉丝：按干粉丝近似
    '粉丝': {'calories': 338, 'protein': 0.8, 'carbs': 83.7, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '龙口粉丝': {'calories': 338, 'protein': 0.8, 'carbs': 83.7, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '燕麦米': {'calories': 389, 'protein': 16.9, 'carbs': 66.3, 'fat': 6.9, 'salt': 0, 'unit': 'g'},
    '红糙米': {'calories': 353, 'protein': 7.4, 'carbs': 77.9, 'fat': 2.8, 'salt': 0, 'unit': 'g'},
    '黑糯米': {'calories': 341, 'protein': 8.3, 'carbs': 73.7, 'fat': 1.7, 'salt': 0, 'unit': 'g'},
    '小土豆': {'calories': 77, 'protein': 2.0, 'carbs': 17.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '土豆': {'calories': 77, 'protein': 2.0, 'carbs': 17.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '红薯': {'calories': 99, 'protein': 1.1, 'carbs': 24.7, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '玉米': {'calories': 112, 'protein': 4.2, 'carbs': 22.8, 'fat': 1.2, 'salt': 0, 'unit': 'g'},
    '藕': {'calories': 70, 'protein': 1.9, 'carbs': 16.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '莲藕': {'calories': 70, 'protein': 1.9, 'carbs': 16.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '九孔莲藕': {'calories': 70, 'protein': 1.9, 'carbs': 16.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    # 蟹类：按膏蟹近似
    '膏蟹': {'calories': 87, 'protein': 18.0, 'carbs': 0, 'fat': 1.5, 'salt': 0, 'unit': 'g'},
    '膏仔蟹': {'calories': 87, 'protein': 18.0, 'carbs': 0, 'fat': 1.5, 'salt': 0, 'unit': 'g'},
    
    # 调料类
    # 盐：100g盐 = 100g盐（直接计算）
    '盐': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 100000, 'unit': 'g'},  # 100g盐 = 100000mg钠 = 约254g盐含量
    '糖': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '白砂糖': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '细砂糖': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '粗砂糖': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'salt': 0, 'unit': 'g'},
    # 酱油：每100g含钠约5757mg，约等于14.6g盐
    '酱油': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},
    '生抽': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},
    # 品牌/同类调味汁：按生抽近似
    '东古酱油': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},
    # 蒸鱼豉油：按生抽近似但略甜
    '蒸鱼豉油': {'calories': 70, 'protein': 5.0, 'carbs': 12.0, 'fat': 0.1, 'salt': 5500, 'unit': 'ml'},
    '蒸鱼汁': {'calories': 70, 'protein': 5.0, 'carbs': 12.0, 'fat': 0.1, 'salt': 5500, 'unit': 'ml'},
    '辣鲜露': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},
    # 芥末（酱）：按常见芥末酱近似（钠含量差异较大，先按0处理；主要盐来自酱油/调味汁）
    '芥末': {'calories': 66, 'protein': 4.4, 'carbs': 5.8, 'fat': 4.0, 'salt': 0, 'unit': 'g'},
    # 蚝油：每100g含钠约4000mg，约等于10.2g盐
    '蚝油': {'calories': 114, 'protein': 2.5, 'carbs': 23.0, 'fat': 0.3, 'salt': 4000, 'unit': 'g'},
    '耗油': {'calories': 114, 'protein': 2.5, 'carbs': 23.0, 'fat': 0.3, 'salt': 4000, 'unit': 'g'},
    '料酒': {'calories': 66, 'protein': 0.3, 'carbs': 0.3, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    # 黄酒：按黄酒/绍兴酒近似
    '黄酒': {'calories': 81, 'protein': 0.5, 'carbs': 5.4, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '白醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    # 味精：每100g含钠约8160mg，约等于20.7g盐
    '味精': {'calories': 268, 'protein': 40.1, 'carbs': 26.5, 'fat': 0.9, 'salt': 8160, 'unit': 'g'},
    '胡椒粉': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '胡椒': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    # 黑胡椒：按黑胡椒粉近似
    '黑胡椒': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '十三香': {'calories': 296, 'protein': 6.0, 'carbs': 68.0, 'fat': 8.0, 'salt': 0, 'unit': 'g'},
    # 沙姜粉：按沙姜/山奈粉近似
    '沙姜粉': {'calories': 300, 'protein': 5.0, 'carbs': 70.0, 'fat': 2.0, 'salt': 0, 'unit': 'g'},
    '沙姜': {'calories': 300, 'protein': 5.0, 'carbs': 70.0, 'fat': 2.0, 'salt': 0, 'unit': 'g'},
    '山奈': {'calories': 300, 'protein': 5.0, 'carbs': 70.0, 'fat': 2.0, 'salt': 0, 'unit': 'g'},
    '小苏打': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '淀粉': {'calories': 364, 'protein': 0.2, 'carbs': 91.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '生粉': {'calories': 364, 'protein': 0.2, 'carbs': 91.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '玉米淀粉': {'calories': 364, 'protein': 0.2, 'carbs': 91.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 水淀粉：按淀粉近似（水无热量，主要计算淀粉部分）
    '水淀粉': {'calories': 364, 'protein': 0.2, 'carbs': 91.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    
    # 油脂类
    '食用油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    # 植物油：按通用植物油近似
    '植物油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    '花生油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    '橄榄油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    '牛油果油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    # 花椒油：按花椒油近似（含花椒提取物，热量与普通食用油相近）
    '花椒油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    
    # 奶制品
    '牛奶': {'calories': 54, 'protein': 3.0, 'carbs': 3.4, 'fat': 3.2, 'salt': 0, 'unit': 'ml'},
    '牛乳': {'calories': 54, 'protein': 3.0, 'carbs': 3.4, 'fat': 3.2, 'salt': 0, 'unit': 'ml'},
    '炼乳': {'calories': 321, 'protein': 7.9, 'carbs': 55.3, 'fat': 8.7, 'salt': 0, 'unit': 'g'},
    '奶油': {'calories': 345, 'protein': 0.7, 'carbs': 2.8, 'fat': 37.0, 'salt': 0, 'unit': 'g'},
    '淡奶油': {'calories': 345, 'protein': 0.7, 'carbs': 2.8, 'fat': 37.0, 'salt': 0, 'unit': 'g'},
    
    # 其他
    # 酒酿/米酒：按发酵糯米制品近似
    '酒酿': {'calories': 100, 'protein': 1.6, 'carbs': 25.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '米酒': {'calories': 100, 'protein': 1.6, 'carbs': 25.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '巧克力': {'calories': 546, 'protein': 4.3, 'carbs': 61.6, 'fat': 31.3, 'salt': 0, 'unit': 'g'},
    '黑巧克力': {'calories': 546, 'protein': 4.3, 'carbs': 61.6, 'fat': 31.3, 'salt': 0, 'unit': 'g'},
    '可可粉': {'calories': 228, 'protein': 19.6, 'carbs': 57.9, 'fat': 13.7, 'salt': 0, 'unit': 'g'},
    '水': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '清水': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '温水': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '气泡水': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '天然水': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    # 原汤：按牛肉汤近似（含少量蛋白质和脂肪）
    '原汤': {'calories': 5, 'protein': 0.5, 'carbs': 0.1, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 雪碧：按柠檬味碳酸饮料近似
    '雪碧': {'calories': 42, 'protein': 0, 'carbs': 10.6, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '雷碧': {'calories': 42, 'protein': 0, 'carbs': 10.6, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    
    # 茶类
    '红茶': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '红茶包': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': '个'},
    '绿茶': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '乌龙茶': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '茉莉花茶': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '抹茶': {'calories': 3, 'protein': 0.2, 'carbs': 0.5, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '抹茶粉': {'calories': 3, 'protein': 0.2, 'carbs': 0.5, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '茶汤': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    
    # 豆制品
    '豆腐': {'calories': 81, 'protein': 8.1, 'carbs': 4.2, 'fat': 3.7, 'salt': 0, 'unit': 'g'},
    '豆芽': {'calories': 18, 'protein': 2.0, 'carbs': 2.9, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 腐竹/豆腐皮：按干腐竹近似
    '腐竹': {'calories': 460, 'protein': 45.0, 'carbs': 15.0, 'fat': 24.0, 'salt': 0, 'unit': 'g'},
    '豆腐皮': {'calories': 460, 'protein': 45.0, 'carbs': 15.0, 'fat': 24.0, 'salt': 0, 'unit': 'g'},
    # 火腿丁：按火腿近似
    '火腿丁': {'calories': 320, 'protein': 16.4, 'carbs': 1.5, 'fat': 27.4, 'salt': 0, 'unit': 'g'},
    # 豆泡/油豆腐：油炸过的豆腐，热量和脂肪含量更高
    '豆泡': {'calories': 245, 'protein': 17.0, 'carbs': 4.2, 'fat': 18.0, 'salt': 0, 'unit': 'g'},
    '油豆腐': {'calories': 245, 'protein': 17.0, 'carbs': 4.2, 'fat': 18.0, 'salt': 0, 'unit': 'g'},
    '豆腐泡': {'calories': 245, 'protein': 17.0, 'carbs': 4.2, 'fat': 18.0, 'salt': 0, 'unit': 'g'},
    
    # 其他肉类
    '排骨': {'calories': 264, 'protein': 18.3, 'carbs': 0, 'fat': 20.4, 'salt': 0, 'unit': 'g'},
    '肉末': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    '肉沫': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    '火腿': {'calories': 320, 'protein': 16.4, 'carbs': 1.5, 'fat': 27.4, 'salt': 0, 'unit': 'g'},
    '牛腱子': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '牛腱': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '熟牛肉': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '猪梅肉': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    '腌牛肉': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '腌肉': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    
    # 更多调料
    '老抽': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},  # 与生抽相同
    '陈醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '香醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '白米醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '米醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    # 豆瓣酱：每100g含钠约6000mg，约等于15.2g盐
    '豆瓣酱': {'calories': 181, 'protein': 13.6, 'carbs': 15.6, 'fat': 6.8, 'salt': 6000, 'unit': 'g'},
    '郫县豆瓣酱': {'calories': 181, 'protein': 13.6, 'carbs': 15.6, 'fat': 6.8, 'salt': 6000, 'unit': 'g'},
    '四川豆瓣酱': {'calories': 181, 'protein': 13.6, 'carbs': 15.6, 'fat': 6.8, 'salt': 6000, 'unit': 'g'},
    '番茄酱': {'calories': 82, 'protein': 4.9, 'carbs': 18.1, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    # 鸡精：每100g含钠约20000mg，约等于50.8g盐
    '鸡精': {'calories': 195, 'protein': 10.7, 'carbs': 43.5, 'fat': 0.3, 'salt': 20000, 'unit': 'g'},
    '鸡粉': {'calories': 195, 'protein': 10.7, 'carbs': 43.5, 'fat': 0.3, 'salt': 20000, 'unit': 'g'},
    '松鲜鲜': {'calories': 195, 'protein': 10.7, 'carbs': 43.5, 'fat': 0.3, 'salt': 20000, 'unit': 'g'},
    '辣椒粉': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '干辣椒': {'calories': 296, 'protein': 15.0, 'carbs': 61.0, 'fat': 12.0, 'salt': 0, 'unit': 'g'},
    '辣椒干': {'calories': 296, 'protein': 15.0, 'carbs': 61.0, 'fat': 12.0, 'salt': 0, 'unit': 'g'},
    '泡椒': {'calories': 30, 'protein': 1.0, 'carbs': 6.0, 'fat': 0.2, 'salt': 2000, 'unit': 'g'},
    '白胡椒粉': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '白胡椒': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '白胡椒碎': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '白胡椒粒': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '花椒': {'calories': 258, 'protein': 6.7, 'carbs': 66.5, 'fat': 8.9, 'salt': 0, 'unit': 'g'},
    '八角': {'calories': 195, 'protein': 3.8, 'carbs': 75.4, 'fat': 5.6, 'salt': 0, 'unit': 'g'},
    '桂皮': {'calories': 174, 'protein': 4.6, 'carbs': 80.0, 'fat': 1.2, 'salt': 0, 'unit': 'g'},
    '香叶': {'calories': 313, 'protein': 7.5, 'carbs': 75.0, 'fat': 8.4, 'salt': 0, 'unit': 'g'},
    '草果': {'calories': 207, 'protein': 8.4, 'carbs': 68.0, 'fat': 7.0, 'salt': 0, 'unit': 'g'},
    # 咖喱粉：按常见值
    '咖喱粉': {'calories': 325, 'protein': 12.0, 'carbs': 55.0, 'fat': 13.0, 'salt': 0, 'unit': 'g'},
    '咖喱': {'calories': 325, 'protein': 12.0, 'carbs': 55.0, 'fat': 13.0, 'salt': 0, 'unit': 'g'},
    # 沙嗲酱：按常见值
    '沙嗲酱': {'calories': 320, 'protein': 8.0, 'carbs': 25.0, 'fat': 22.0, 'salt': 2000, 'unit': 'g'},
    # 圆椒酱：按辣椒酱近似
    '圆椒酱': {'calories': 150, 'protein': 2.0, 'carbs': 30.0, 'fat': 3.0, 'salt': 3000, 'unit': 'g'},
    # 当归片：中药材，按常见值
    '当归': {'calories': 280, 'protein': 16.0, 'carbs': 60.0, 'fat': 4.0, 'salt': 0, 'unit': 'g'},
    '当归片': {'calories': 280, 'protein': 16.0, 'carbs': 60.0, 'fat': 4.0, 'salt': 0, 'unit': 'g'},
    # 浓缩鸡汁：按鸡精近似但更浓
    '浓缩鸡汁': {'calories': 150, 'protein': 8.0, 'carbs': 20.0, 'fat': 0.2, 'salt': 15000, 'unit': 'ml'},
    # 鸡油：按鸡脂肪近似
    '鸡油': {'calories': 900, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    # 辣酒：按黄酒近似
    '辣酒': {'calories': 81, 'protein': 0.5, 'carbs': 5.4, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    # 香油：芝麻油
    '香油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    '芝麻油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    '熟芝麻': {'calories': 559, 'protein': 19.1, 'carbs': 21.6, 'fat': 46.1, 'salt': 0, 'unit': 'g'},
    '白芝麻': {'calories': 559, 'protein': 19.1, 'carbs': 21.6, 'fat': 46.1, 'salt': 0, 'unit': 'g'},
    '芝麻': {'calories': 559, 'protein': 19.1, 'carbs': 21.6, 'fat': 46.1, 'salt': 0, 'unit': 'g'},
    # 花生米：炸好的花生米，按油炸花生近似
    '花生米': {'calories': 600, 'protein': 25.0, 'carbs': 16.0, 'fat': 50.0, 'salt': 0, 'unit': 'g'},
    '炸花生米': {'calories': 600, 'protein': 25.0, 'carbs': 16.0, 'fat': 50.0, 'salt': 0, 'unit': 'g'},
    '花生': {'calories': 600, 'protein': 25.0, 'carbs': 16.0, 'fat': 50.0, 'salt': 0, 'unit': 'g'},
    '色拉油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    # 蜂蜜：按常见值
    '蜂蜜': {'calories': 304, 'protein': 0.3, 'carbs': 75.6, 'fat': 0, 'salt': 0, 'unit': 'g'},
    # 黄栀子：天然食用色素，营养值极低
    '黄栀子': {'calories': 5, 'protein': 0.1, 'carbs': 1.0, 'fat': 0, 'salt': 0, 'unit': 'g'},
    
    # 水果类
    '草莓': {'calories': 32, 'protein': 1.0, 'carbs': 7.7, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '菠萝': {'calories': 50, 'protein': 0.5, 'carbs': 12.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '新鲜菠萝': {'calories': 50, 'protein': 0.5, 'carbs': 12.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '西瓜': {'calories': 30, 'protein': 0.6, 'carbs': 7.6, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '柠檬': {'calories': 29, 'protein': 1.1, 'carbs': 9.3, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '柠檬汁': {'calories': 22, 'protein': 0.4, 'carbs': 6.9, 'fat': 0.2, 'salt': 0, 'unit': 'ml'},
    # 小青桔/金桔：按金桔近似
    '小青桔': {'calories': 55, 'protein': 1.0, 'carbs': 13.7, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '金桔': {'calories': 55, 'protein': 1.0, 'carbs': 13.7, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    # 葡萄汁：按常见值
    '葡萄汁': {'calories': 60, 'protein': 0.3, 'carbs': 14.5, 'fat': 0.1, 'salt': 0, 'unit': 'ml'},
    # 水溶C：按维生素C饮料近似
    '水溶C': {'calories': 35, 'protein': 0, 'carbs': 8.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '柠檬味水溶C': {'calories': 35, 'protein': 0, 'carbs': 8.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '话梅': {'calories': 168, 'protein': 0.8, 'carbs': 42.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '话梅糖浆': {'calories': 304, 'protein': 0, 'carbs': 78.0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    # 杨梅：按常见值（每100g）
    '杨梅': {'calories': 30, 'protein': 0.8, 'carbs': 6.7, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    # 荔枝：按常见值（每100g）
    '荔枝': {'calories': 70, 'protein': 0.9, 'carbs': 16.5, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    
    # 其他食材
    '吐司': {'calories': 265, 'protein': 8.3, 'carbs': 49.7, 'fat': 4.2, 'salt': 0, 'unit': 'g'},
    '黄油': {'calories': 717, 'protein': 0.5, 'carbs': 0.1, 'fat': 81.1, 'salt': 0, 'unit': 'g'},
    '奶油奶酪': {'calories': 342, 'protein': 6.2, 'carbs': 3.2, 'fat': 34.4, 'salt': 0, 'unit': 'g'},
    '蛋白': {'calories': 52, 'protein': 10.9, 'carbs': 1.0, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '韭菜': {'calories': 26, 'protein': 2.4, 'carbs': 4.5, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '芹菜': {'calories': 16, 'protein': 0.8, 'carbs': 3.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '西芹': {'calories': 16, 'protein': 0.8, 'carbs': 3.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '蘑菇': {'calories': 22, 'protein': 2.7, 'carbs': 4.1, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '鲜菇': {'calories': 22, 'protein': 2.7, 'carbs': 4.1, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 口蘑：白蘑菇/双孢菇
    '口蘑': {'calories': 22, 'protein': 2.7, 'carbs': 4.1, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '白蘑菇': {'calories': 22, 'protein': 2.7, 'carbs': 4.1, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 平菇：按平菇/蚝菇近似
    '平菇': {'calories': 24, 'protein': 1.9, 'carbs': 4.6, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '蚝菇': {'calories': 24, 'protein': 1.9, 'carbs': 4.6, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    # 杏鲍菇：按常见营养表近似
    '杏鲍菇': {'calories': 32, 'protein': 3.0, 'carbs': 6.0, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    # 鹿茸菇：按鹿茸菇/茶树菇近似
    '鹿茸菇': {'calories': 30, 'protein': 2.5, 'carbs': 5.5, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '茶树菇': {'calories': 30, 'protein': 2.5, 'carbs': 5.5, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '泡发干香菇': {'calories': 19, 'protein': 2.2, 'carbs': 3.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '青椒': {'calories': 22, 'protein': 1.0, 'carbs': 5.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '红椒': {'calories': 22, 'protein': 1.0, 'carbs': 5.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '青红椒': {'calories': 22, 'protein': 1.0, 'carbs': 5.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '鲜河粉': {'calories': 140, 'protein': 3.0, 'carbs': 30.0, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '木薯粉': {'calories': 360, 'protein': 0.2, 'carbs': 88.7, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '干淀粉': {'calories': 364, 'protein': 0.2, 'carbs': 91.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    
    # 糖类
    '冰糖': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '白糖': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '红糖': {'calories': 389, 'protein': 0.7, 'carbs': 96.6, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '黑糖': {'calories': 389, 'protein': 0.7, 'carbs': 96.6, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '糖浆': {'calories': 304, 'protein': 0, 'carbs': 78.0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    
    # 饮品相关
    '咖啡伴侣': {'calories': 545, 'protein': 0.7, 'carbs': 58.0, 'fat': 35.0, 'salt': 0, 'unit': 'g'},
    # 椰奶/椰汁：按罐装椰奶近似（wholefood 365 椰汁用此）
    '椰奶': {'calories': 190, 'protein': 2.0, 'carbs': 6.0, 'fat': 18.0, 'salt': 0, 'unit': 'ml'},
    '椰汁': {'calories': 190, 'protein': 2.0, 'carbs': 6.0, 'fat': 18.0, 'salt': 0, 'unit': 'ml'},
    # 咖啡豆：按咖啡豆近似（萃取后咖啡液热量较低）
    '咖啡豆': {'calories': 1, 'protein': 0.1, 'carbs': 0.1, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '咖啡液': {'calories': 1, 'protein': 0.1, 'carbs': 0.1, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '厚乳': {'calories': 65, 'protein': 3.0, 'carbs': 4.5, 'fat': 3.5, 'salt': 0, 'unit': 'ml'},
    '纯牛奶': {'calories': 54, 'protein': 3.0, 'carbs': 3.4, 'fat': 3.2, 'salt': 0, 'unit': 'ml'},
    # 燕麦奶：按燕麦奶近似
    '燕麦奶': {'calories': 45, 'protein': 1.0, 'carbs': 6.5, 'fat': 1.5, 'salt': 0, 'unit': 'ml'},
    '冰块': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '冰': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'g'},
    
    # 其他
    '红枣': {'calories': 264, 'protein': 2.1, 'carbs': 67.8, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '红枣丝': {'calories': 264, 'protein': 2.1, 'carbs': 67.8, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    # 虫草花：按干虫草花近似
    '虫草花': {'calories': 300, 'protein': 25.0, 'carbs': 40.0, 'fat': 2.0, 'salt': 0, 'unit': 'g'},
    # 枸杞：按干枸杞近似
    '枸杞': {'calories': 258, 'protein': 13.0, 'carbs': 43.0, 'fat': 2.7, 'salt': 0, 'unit': 'g'},
    # 蜜枣：按蜜饯红枣近似
    '蜜枣': {'calories': 320, 'protein': 1.5, 'carbs': 78.0, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    # 陈皮：干橘皮，按常见值
    '陈皮': {'calories': 324, 'protein': 8.0, 'carbs': 79.0, 'fat': 1.4, 'salt': 0, 'unit': 'g'},
    # 红豆：按干红豆近似
    '红豆': {'calories': 324, 'protein': 20.2, 'carbs': 63.0, 'fat': 0.6, 'salt': 0, 'unit': 'g'},
    # 绿豆：按干绿豆近似
    '绿豆': {'calories': 316, 'protein': 21.6, 'carbs': 62.0, 'fat': 0.8, 'salt': 0, 'unit': 'g'},
    # 龙骨：猪脊骨，按排骨近似但略低脂肪
    '龙骨': {'calories': 240, 'protein': 18.0, 'carbs': 0, 'fat': 18.0, 'salt': 0, 'unit': 'g'},
    # 鸡脚：按鸡爪近似
    '鸡脚': {'calories': 215, 'protein': 19.4, 'carbs': 0, 'fat': 14.6, 'salt': 0, 'unit': 'g'},
    '鸡爪': {'calories': 215, 'protein': 19.4, 'carbs': 0, 'fat': 14.6, 'salt': 0, 'unit': 'g'},
    '玫瑰': {'calories': 316, 'protein': 4.0, 'carbs': 75.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 玫瑰花酱：按玫瑰果酱近似
    '玫瑰花酱': {'calories': 280, 'protein': 0.5, 'carbs': 70.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 螺丝椒：按长辣椒/线椒近似
    '线椒': {'calories': 22, 'protein': 1.0, 'carbs': 5.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '螺丝椒': {'calories': 40, 'protein': 1.9, 'carbs': 8.8, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    # 前腿肉：按猪前腿肉近似，略瘦于五花肉
    '前腿肉': {'calories': 230, 'protein': 20.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    # 头抽：按生抽/头抽酱油近似
    '头抽': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'ml'},
    # 豆豉：按发酵黑豆制品近似
    '豆豉': {'calories': 259, 'protein': 24.1, 'carbs': 36.8, 'fat': 3.0, 'salt': 2637, 'unit': 'g'},
    # 猪油：按猪脂肪近似
    '猪油': {'calories': 902, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'g'},
    # 鸡饭老抽：按老抽近似
    '鸡饭老抽': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'ml'},
    '龙牌酱油': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'ml'},
    
    # 特殊单位换算（在find_nutrition中处理）
    '个': {'鸡蛋': {'calories': 72, 'protein': 6.5, 'carbs': 0.5, 'fat': 4.4, 'salt': 0, 'unit': '个'},  # 约50g一个鸡蛋
           '面饼': {'calories': 280, 'protein': 9.0, 'carbs': 58.0, 'fat': 1.0, 'salt': 0, 'unit': '个'}},  # 约100g一个面饼
    '头': {'蒜': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': '头'}},  # 约100g一头蒜
    '瓣': {'蒜': {'calories': 4, 'protein': 0.2, 'carbs': 0.9, 'fat': 0.01, 'salt': 0, 'unit': '瓣'}},  # 约3g一瓣蒜
    '滴': {'白醋': {'calories': 0.03, 'protein': 0, 'carbs': 0.008, 'fat': 0, 'salt': 0, 'unit': '滴'}},  # 约0.5ml一滴
    '杯': {'水': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': '杯'}},  # 约250ml一杯
}

# 忽略的食材（不计算营养成分）
IGNORE_INGREDIENTS = {'份', '一份', '总共', '总量', '闷泡', '75摄氏度热水', '油 500ml', '杯', '碳水', '蛋白质', '纤维'}

def find_nutrition(name, quantity, unit):
    """
    查找食材的营养成分
    """
    name_clean = name.strip()
    
    # 处理特殊单位（个、头、瓣、滴、杯）
    if unit in ['个', '头', '瓣', '滴', '杯']:
        if unit in NUTRITION_DB and name_clean in NUTRITION_DB[unit]:
            result = NUTRITION_DB[unit][name_clean].copy()
            if 'unit' not in result:
                result['unit'] = unit
            return result
        
        # 如果没有特殊单位数据，尝试按名称查找并换算
        if name_clean in NUTRITION_DB:
            base_nutrition = NUTRITION_DB[name_clean].copy()
            # 根据单位换算
            if unit == '个':
                if '鸡蛋' in name_clean or '蛋' in name_clean:
                    return {'calories': 72, 'protein': 6.5, 'carbs': 0.5, 'fat': 4.4, 'salt': 0, 'unit': '个'}
                elif '面饼' in name_clean:
                    return {'calories': 280, 'protein': 9.0, 'carbs': 58.0, 'fat': 1.0, 'salt': 0, 'unit': '个'}
                else:
                    # 默认按100g计算
                    multiplier = 1.0
            elif unit == '头' and '蒜' in name_clean:
                return {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': '头'}
            elif unit == '瓣' and '蒜' in name_clean:
                return {'calories': 4, 'protein': 0.2, 'carbs': 0.9, 'fat': 0.01, 'salt': 0, 'unit': '瓣'}
            elif unit == '滴':
                # 一滴约0.5ml
                base_unit = base_nutrition.get('unit', 'ml')
                multiplier = 0.5 / 100
                salt_mg = base_nutrition.get('salt', 0) * multiplier * 100
                salt_g = salt_mg / 1000 * 2.54
                return {
                    'calories': base_nutrition['calories'] * multiplier,
                    'protein': base_nutrition['protein'] * multiplier,
                    'carbs': base_nutrition['carbs'] * multiplier,
                    'fat': base_nutrition['fat'] * multiplier,
                    'salt': round(salt_g, 2),
                    'unit': '滴'
                }
            elif unit == '杯':
                # 一杯约250ml，假设是水
                if '水' in name_clean:
                    return {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': '杯'}
                else:
                    # 其他液体按250ml计算
                    base_unit = base_nutrition.get('unit', 'ml')
                    multiplier = 250 / 100 if base_unit == 'ml' else 250 / 100
                    salt_mg = base_nutrition.get('salt', 0) * multiplier * 100
                    salt_g = salt_mg / 1000 * 2.54
                    return {
                        'calories': base_nutrition['calories'] * multiplier,
                        'protein': base_nutrition['protein'] * multiplier,
                        'carbs': base_nutrition['carbs'] * multiplier,
                        'fat': base_nutrition['fat'] * multiplier,
                        'salt': round(salt_g, 2),
                        'unit': '杯'
                    }
    
    # 直接查找
    if name_clean in NUTRITION_DB:
        result = NUTRITION_DB[name_clean].copy()
        if 'unit' not in result:
            result['unit'] = 'g'  # 默认单位
        return result
    
    # 模糊匹配
    for key, value in NUTRITION_DB.items():
        if isinstance(value, dict) and 'calories' in value:
            if key in name_clean or name_clean in key:
                result = value.copy()
                if 'unit' not in result:
                    result['unit'] = 'g'
                return result
    
    # 默认值（如果找不到）
    print(f"  警告: 未找到食材 '{name_clean}' 的营养成分数据，使用默认值")
    return {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'g'}

def calculate_ingredient_nutrition(ingredient):
    """
    计算单个食材的营养成分
    """
    name = ingredient['name']
    quantity = ingredient['quantity']
    unit = ingredient['unit']
    
    # 获取基础营养成分
    base_nutrition = find_nutrition(name, quantity, unit)
    base_unit = base_nutrition.get('unit', 'g')
    
    # 处理特殊单位（已经在find_nutrition中按单位计算好了）
    if unit in ['个', '头', '瓣', '滴']:
        # 特殊单位已经按单位计算，直接乘以数量
        multiplier = quantity
    elif unit == '杯':
        # 杯需要特殊处理，因为可能是食材名称
        if name == '杯':
            # 如果食材名称就是"杯"，跳过
            return {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0}
        else:
            # 如果单位是杯，按250ml计算
            base_unit = base_nutrition.get('unit', 'ml')
            if base_unit == 'ml':
                multiplier = quantity * 250 / 100
            else:
                multiplier = quantity * 250 / 100
    else:
        # 计算实际用量
        if base_unit == 'g':
            # 如果基础单位是克
            if unit == 'g' or unit == '克':
                multiplier = quantity / 100
            elif unit == 'ml' or unit == '毫升':
                # 假设密度为1，1ml = 1g
                multiplier = quantity / 100
            else:
                multiplier = quantity / 100
        elif base_unit == 'ml':
            # 如果基础单位是毫升
            if unit == 'ml' or unit == '毫升':
                multiplier = quantity / 100
            elif unit == 'g' or unit == '克':
                # 假设密度为1
                multiplier = quantity / 100
            else:
                multiplier = quantity / 100
        else:
            multiplier = quantity / 100
    
    # 计算营养成分（包括盐含量）
    # 特殊处理：如果食材是"盐"，直接使用用量作为盐含量
    if name.strip() == '盐':
        salt_g = quantity if unit in ['g', '克'] else quantity  # 盐的用量就是盐含量
    else:
        # salt字段存储的是钠含量（毫克/100g），需要转换为盐含量（克）
        # 盐含量 = 钠含量(mg) / 1000 * 2.54
        salt_mg_per_100g = base_nutrition.get('salt', 0)
        # 计算实际用量（克）
        if base_unit == 'g' or base_unit == '克':
            actual_quantity_g = quantity if unit in ['g', '克'] else (quantity if unit in ['ml', '毫升'] else quantity)
        elif base_unit == 'ml' or base_unit == '毫升':
            actual_quantity_g = quantity if unit in ['ml', '毫升'] else (quantity if unit in ['g', '克'] else quantity)
        else:
            actual_quantity_g = quantity * 100 * multiplier  # 转换为克
        
        salt_mg_total = salt_mg_per_100g * (actual_quantity_g / 100)
        salt_g = salt_mg_total / 1000 * 2.54  # 转换为盐含量（克）
    
    return {
        'calories': base_nutrition['calories'] * multiplier,
        'protein': base_nutrition['protein'] * multiplier,
        'carbs': base_nutrition['carbs'] * multiplier,
        'fat': base_nutrition['fat'] * multiplier,
        'salt': round(salt_g, 2)  # 盐含量（克），保留2位小数
    }

def calculate_recipe_nutrition(recipe):
    """
    计算整个菜谱的营养成分
    """
    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    total_salt = 0  # 盐含量（克）
    
    if not recipe.get('ingredients'):
        return None
    
    for ingredient in recipe['ingredients']:
        name = ingredient['name'].strip()
        
        # 跳过忽略的食材
        if name in IGNORE_INGREDIENTS:
            continue
        
        # 跳过数量为0或空的食材
        if ingredient.get('quantity', 0) == 0:
            continue
        
        try:
            nutrition = calculate_ingredient_nutrition(ingredient)
            total_calories += nutrition['calories']
            total_protein += nutrition['protein']
            total_carbs += nutrition['carbs']
            total_fat += nutrition['fat']
            total_salt += nutrition.get('salt', 0)
        except Exception as e:
            print(f"  警告: 计算食材 '{name}' 时出错: {e}")
            continue
    
    return {
        'calories': round(total_calories, 1),
        'protein': round(total_protein, 1),
        'carbs': round(total_carbs, 1),
        'fat': round(total_fat, 1),
        'salt': round(total_salt, 2)  # 盐含量保留2位小数
    }

def main():
    """
    主函数：计算所有菜谱的营养成分并更新JSON文件
    """
    # 读取recipes.json
    with open('recipes.json', 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    print(f"开始计算 {len(recipes)} 个菜谱的营养成分...")
    print("=" * 60)
    
    updated_count = 0
    for i, recipe in enumerate(recipes, 1):
        title = recipe['title']
        print(f"\n[{i}/{len(recipes)}] 计算: {title}")
        
        nutrition = calculate_recipe_nutrition(recipe)
        
        if nutrition:
            recipe['nutrition'] = nutrition
            updated_count += 1
            print(f"  ✓ 热量: {nutrition['calories']} 大卡")
            print(f"  ✓ 蛋白质: {nutrition['protein']} 克")
            print(f"  ✓ 碳水: {nutrition['carbs']} 克")
            print(f"  ✓ 脂肪: {nutrition['fat']} 克")
            print(f"  ✓ 盐: {nutrition['salt']} 克")
        else:
            print(f"  ⚠ 无食材数据，跳过")
    
    # 保存更新后的JSON文件
    with open('recipes.json', 'w', encoding='utf-8') as f:
        json.dump(recipes, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✅ 完成！已更新 {updated_count} 个菜谱的营养成分")
    print(f"✅ 文件已保存到 recipes.json")

if __name__ == '__main__':
    main()
