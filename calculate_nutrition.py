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
    
    # 肉类
    '牛里脊': {'calories': 107, 'protein': 22.2, 'carbs': 0, 'fat': 2.3, 'salt': 0, 'unit': 'g'},
    '牛肉': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '鸡肉': {'calories': 167, 'protein': 19.3, 'carbs': 0, 'fat': 9.4, 'salt': 0, 'unit': 'g'},
    # 去骨鸡腿肉：按去皮鸡腿生肉近似，略高脂肪
    '去骨鸡腿肉': {'calories': 180, 'protein': 18.0, 'carbs': 0, 'fat': 12.0, 'salt': 0, 'unit': 'g'},
    '猪肉': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    '虾': {'calories': 93, 'protein': 18.6, 'carbs': 2.8, 'fat': 0.8, 'salt': 0, 'unit': 'g'},
    # 贝类/螺类（常见值，按每100g可食部分估算）
    # 参考：USDA/中国食物成分表中同类贝类（螺/海螺/田螺）营养范围
    '花螺': {'calories': 110, 'protein': 20.0, 'carbs': 3.0, 'fat': 1.5, 'salt': 0, 'unit': 'g'},
    
    # 蔬菜类（天然含钠量很少）
    '番茄': {'calories': 18, 'protein': 0.9, 'carbs': 3.5, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '西红柿': {'calories': 18, 'protein': 0.9, 'carbs': 3.5, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '西兰花': {'calories': 34, 'protein': 2.8, 'carbs': 6.6, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '西蓝花': {'calories': 34, 'protein': 2.8, 'carbs': 6.6, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '茄子': {'calories': 25, 'protein': 1.1, 'carbs': 5.4, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '白菜': {'calories': 16, 'protein': 1.5, 'carbs': 3.2, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 娃娃菜：按小棵大白菜近似
    '娃娃菜': {'calories': 15, 'protein': 1.3, 'carbs': 2.8, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '青菜': {'calories': 15, 'protein': 1.5, 'carbs': 2.4, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '胡萝卜': {'calories': 41, 'protein': 0.9, 'carbs': 9.6, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '洋葱': {'calories': 40, 'protein': 1.1, 'carbs': 9.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '大葱': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '小葱': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '香葱': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '葱': {'calories': 30, 'protein': 1.7, 'carbs': 6.5, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '蒜': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '蒜头': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '蒜蓉': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '蒜末': {'calories': 149, 'protein': 6.4, 'carbs': 33.1, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '姜': {'calories': 80, 'protein': 1.8, 'carbs': 17.8, 'fat': 0.8, 'salt': 0, 'unit': 'g'},
    '紫菜': {'calories': 207, 'protein': 28.2, 'carbs': 44.1, 'fat': 1.1, 'salt': 0, 'unit': 'g'},
    '香菜': {'calories': 23, 'protein': 2.1, 'carbs': 3.7, 'fat': 0.5, 'salt': 0, 'unit': 'g'},
    '小米辣': {'calories': 40, 'protein': 1.9, 'carbs': 8.8, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '羽衣甘蓝': {'calories': 49, 'protein': 4.3, 'carbs': 8.8, 'fat': 0.9, 'salt': 0, 'unit': 'g'},
    '小卷心菜': {'calories': 25, 'protein': 1.3, 'carbs': 5.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    
    # 主食类
    '面饼': {'calories': 280, 'protein': 9.0, 'carbs': 58.0, 'fat': 1.0, 'salt': 0, 'unit': 'g'},
    '面条': {'calories': 280, 'protein': 9.0, 'carbs': 58.0, 'fat': 1.0, 'salt': 0, 'unit': 'g'},
    '燕麦米': {'calories': 389, 'protein': 16.9, 'carbs': 66.3, 'fat': 6.9, 'salt': 0, 'unit': 'g'},
    '红糙米': {'calories': 353, 'protein': 7.4, 'carbs': 77.9, 'fat': 2.8, 'salt': 0, 'unit': 'g'},
    '黑糯米': {'calories': 341, 'protein': 8.3, 'carbs': 73.7, 'fat': 1.7, 'salt': 0, 'unit': 'g'},
    '小土豆': {'calories': 77, 'protein': 2.0, 'carbs': 17.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '土豆': {'calories': 77, 'protein': 2.0, 'carbs': 17.8, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '红薯': {'calories': 99, 'protein': 1.1, 'carbs': 24.7, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '玉米': {'calories': 112, 'protein': 4.2, 'carbs': 22.8, 'fat': 1.2, 'salt': 0, 'unit': 'g'},
    '藕': {'calories': 70, 'protein': 1.9, 'carbs': 16.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    
    # 调料类
    # 盐：100g盐 = 100g盐（直接计算）
    '盐': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 100000, 'unit': 'g'},  # 100g盐 = 100000mg钠 = 约254g盐含量
    '糖': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '白砂糖': {'calories': 387, 'protein': 0, 'carbs': 100, 'fat': 0, 'salt': 0, 'unit': 'g'},
    # 酱油：每100g含钠约5757mg，约等于14.6g盐
    '酱油': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},
    '生抽': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},
    # 品牌/同类调味汁：按生抽近似
    '东古酱油': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},
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
    # 黑胡椒：按黑胡椒粉近似
    '黑胡椒': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '十三香': {'calories': 296, 'protein': 6.0, 'carbs': 68.0, 'fat': 8.0, 'salt': 0, 'unit': 'g'},
    '小苏打': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '淀粉': {'calories': 364, 'protein': 0.2, 'carbs': 91.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '玉米淀粉': {'calories': 364, 'protein': 0.2, 'carbs': 91.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    
    # 油脂类
    '食用油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    # 植物油：按通用植物油近似
    '植物油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    '花生油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    '橄榄油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    '牛油果油': {'calories': 884, 'protein': 0, 'carbs': 0, 'fat': 100, 'salt': 0, 'unit': 'ml'},
    
    # 奶制品
    '牛奶': {'calories': 54, 'protein': 3.0, 'carbs': 3.4, 'fat': 3.2, 'salt': 0, 'unit': 'ml'},
    '奶油': {'calories': 345, 'protein': 0.7, 'carbs': 2.8, 'fat': 37.0, 'salt': 0, 'unit': 'g'},
    '淡奶油': {'calories': 345, 'protein': 0.7, 'carbs': 2.8, 'fat': 37.0, 'salt': 0, 'unit': 'g'},
    
    # 其他
    '巧克力': {'calories': 546, 'protein': 4.3, 'carbs': 61.6, 'fat': 31.3, 'salt': 0, 'unit': 'g'},
    '黑巧克力': {'calories': 546, 'protein': 4.3, 'carbs': 61.6, 'fat': 31.3, 'salt': 0, 'unit': 'g'},
    '可可粉': {'calories': 228, 'protein': 19.6, 'carbs': 57.9, 'fat': 13.7, 'salt': 0, 'unit': 'g'},
    '水': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '清水': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    
    # 茶类
    '红茶': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '绿茶': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': 'g'},
    '茶汤': {'calories': 2, 'protein': 0.1, 'carbs': 0.4, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    
    # 豆制品
    '豆腐': {'calories': 81, 'protein': 8.1, 'carbs': 4.2, 'fat': 3.7, 'salt': 0, 'unit': 'g'},
    '豆芽': {'calories': 18, 'protein': 2.0, 'carbs': 2.9, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    
    # 其他肉类
    '排骨': {'calories': 264, 'protein': 18.3, 'carbs': 0, 'fat': 20.4, 'salt': 0, 'unit': 'g'},
    '肉末': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    '肉沫': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    '火腿': {'calories': 320, 'protein': 16.4, 'carbs': 1.5, 'fat': 27.4, 'salt': 0, 'unit': 'g'},
    '牛腱子': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '猪梅肉': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    '腌牛肉': {'calories': 250, 'protein': 26.0, 'carbs': 0, 'fat': 15.0, 'salt': 0, 'unit': 'g'},
    '腌肉': {'calories': 242, 'protein': 20.3, 'carbs': 0, 'fat': 16.6, 'salt': 0, 'unit': 'g'},
    
    # 更多调料
    '老抽': {'calories': 63, 'protein': 5.6, 'carbs': 9.9, 'fat': 0.1, 'salt': 5757, 'unit': 'g'},  # 与生抽相同
    '陈醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '香醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    '白米醋': {'calories': 6, 'protein': 0, 'carbs': 1.5, 'fat': 0, 'salt': 0, 'unit': 'ml'},
    # 豆瓣酱：每100g含钠约6000mg，约等于15.2g盐
    '豆瓣酱': {'calories': 181, 'protein': 13.6, 'carbs': 15.6, 'fat': 6.8, 'salt': 6000, 'unit': 'g'},
    '番茄酱': {'calories': 82, 'protein': 4.9, 'carbs': 18.1, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    # 鸡精：每100g含钠约20000mg，约等于50.8g盐
    '鸡精': {'calories': 195, 'protein': 10.7, 'carbs': 43.5, 'fat': 0.3, 'salt': 20000, 'unit': 'g'},
    '鸡粉': {'calories': 195, 'protein': 10.7, 'carbs': 43.5, 'fat': 0.3, 'salt': 20000, 'unit': 'g'},
    '辣椒粉': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '干辣椒': {'calories': 296, 'protein': 15.0, 'carbs': 61.0, 'fat': 12.0, 'salt': 0, 'unit': 'g'},
    '白胡椒粉': {'calories': 316, 'protein': 10.4, 'carbs': 63.9, 'fat': 3.3, 'salt': 0, 'unit': 'g'},
    '花椒': {'calories': 258, 'protein': 6.7, 'carbs': 66.5, 'fat': 8.9, 'salt': 0, 'unit': 'g'},
    '八角': {'calories': 195, 'protein': 3.8, 'carbs': 75.4, 'fat': 5.6, 'salt': 0, 'unit': 'g'},
    '桂皮': {'calories': 174, 'protein': 4.6, 'carbs': 80.0, 'fat': 1.2, 'salt': 0, 'unit': 'g'},
    '香叶': {'calories': 313, 'protein': 7.5, 'carbs': 75.0, 'fat': 8.4, 'salt': 0, 'unit': 'g'},
    '草果': {'calories': 207, 'protein': 8.4, 'carbs': 68.0, 'fat': 7.0, 'salt': 0, 'unit': 'g'},
    
    # 水果类
    '菠萝': {'calories': 50, 'protein': 0.5, 'carbs': 12.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '新鲜菠萝': {'calories': 50, 'protein': 0.5, 'carbs': 12.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '柠檬': {'calories': 29, 'protein': 1.1, 'carbs': 9.3, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '柠檬汁': {'calories': 22, 'protein': 0.4, 'carbs': 6.9, 'fat': 0.2, 'salt': 0, 'unit': 'ml'},
    '话梅': {'calories': 168, 'protein': 0.8, 'carbs': 42.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    
    # 其他食材
    '吐司': {'calories': 265, 'protein': 8.3, 'carbs': 49.7, 'fat': 4.2, 'salt': 0, 'unit': 'g'},
    '黄油': {'calories': 717, 'protein': 0.5, 'carbs': 0.1, 'fat': 81.1, 'salt': 0, 'unit': 'g'},
    '奶油奶酪': {'calories': 342, 'protein': 6.2, 'carbs': 3.2, 'fat': 34.4, 'salt': 0, 'unit': 'g'},
    '蛋白': {'calories': 52, 'protein': 10.9, 'carbs': 1.0, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '韭菜': {'calories': 26, 'protein': 2.4, 'carbs': 4.5, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '蘑菇': {'calories': 22, 'protein': 2.7, 'carbs': 4.1, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    # 杏鲍菇：按常见营养表近似
    '杏鲍菇': {'calories': 32, 'protein': 3.0, 'carbs': 6.0, 'fat': 0.3, 'salt': 0, 'unit': 'g'},
    '泡发干香菇': {'calories': 19, 'protein': 2.2, 'carbs': 3.3, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    '青椒': {'calories': 22, 'protein': 1.0, 'carbs': 5.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
    '红椒': {'calories': 22, 'protein': 1.0, 'carbs': 5.4, 'fat': 0.2, 'salt': 0, 'unit': 'g'},
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
    '厚乳': {'calories': 65, 'protein': 3.0, 'carbs': 4.5, 'fat': 3.5, 'salt': 0, 'unit': 'ml'},
    '纯牛奶': {'calories': 54, 'protein': 3.0, 'carbs': 3.4, 'fat': 3.2, 'salt': 0, 'unit': 'ml'},
    '冰块': {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0, 'salt': 0, 'unit': 'g'},
    
    # 其他
    '红枣': {'calories': 264, 'protein': 2.1, 'carbs': 67.8, 'fat': 0.4, 'salt': 0, 'unit': 'g'},
    '玫瑰': {'calories': 316, 'protein': 4.0, 'carbs': 75.0, 'fat': 0.1, 'salt': 0, 'unit': 'g'},
    
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
