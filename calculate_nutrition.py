#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确计算每个菜谱的营养成分
根据食材清单和用量，逐一计算并累加营养成分
"""

import json
import re
import os

# 加载营养数据库（从 JSON 文件）
def load_nutrition_database():
    """
    从 nutrition_db.json 加载营养数据库
    """
    nutrition_db_path = 'nutrition_db.json'
    if not os.path.exists(nutrition_db_path):
        raise FileNotFoundError(f"未找到 {nutrition_db_path}，请确保该文件存在")
    
    try:
        with open(nutrition_db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            nutrition_db = data.get('nutrition_db', {})
            if not nutrition_db:
                raise ValueError(f"{nutrition_db_path} 中未找到 nutrition_db 数据")
            print(f"✅ 已从 nutrition_db.json 加载营养数据库（共 {len([k for k in nutrition_db.keys() if k not in ['个', '头', '瓣', '滴', '杯']])} 种食材）")
            return nutrition_db
    except Exception as e:
        raise RuntimeError(f"加载营养数据库失败: {e}")

# 加载营养数据库
NUTRITION_DB = load_nutrition_database()

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
