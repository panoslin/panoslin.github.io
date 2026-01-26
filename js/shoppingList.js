/**
 * 购物清单管理模块
 * 负责食材收集、合并、分类和持久化
 */

// 食材分类映射
const INGREDIENT_CATEGORIES = {
    // 蔬菜类
    '蔬菜': ['白菜', '青菜', '菠菜', '生菜', '韭菜', '芹菜', '香菜', '小葱', '大葱', '青葱', '香葱', '洋葱', '红洋葱', '蒜', '姜', '蒜末', '姜片', '葱段', '葱花', '蒜蓉', '蒜酥', '胡萝卜', '白萝卜', '土豆', '小土豆', '红薯', '紫薯', '莲藕', '藕', '茄子', '西红柿', '番茄', '黄瓜', '青椒', '红椒', '彩椒', '小米辣', '辣椒', '辣椒粉', '西蓝花', '西兰花', '花菜', '菜花', '蘑菇', '香菇', '泡发干香菇', '金针菇', '平菇', '杏鲍菇', '豆芽', '绿豆芽', '黄豆芽', '豆腐', '豆干', '腐竹', '紫菜', '海带', '木耳', '银耳', '羽衣甘蓝', '小卷心菜'],
    
    // 水果类
    '水果': ['苹果', '梨', '香蕉', '橙子', '橘子', '柠檬', '柠檬汁', '葡萄', '草莓', '蓝莓', '樱桃', '桃子', '杏子', '李子', '芒果', '菠萝', '新鲜菠萝', '西瓜', '哈密瓜', '火龙果', '猕猴桃', '柚子', '石榴', '荔枝', '龙眼', '榴莲', '椰子'],
    
    // 肉类
    '肉类': ['猪肉', '猪肉糜', '猪梅肉', '前臀尖', '排骨', '牛肉', '牛里脊', '牛腱子', '金钱腱', '羊肉', '鸡肉', '鸡胸肉', '鸡腿', '鸡翅', '鸭肉', '鹅肉', '火腿', '培根', '香肠', '腊肉', '腌肉', '肉沫', '肉末', '肉丝', '肉片'],
    
    // 海鲜类
    '海鲜': ['鱼', '草鱼', '鲫鱼', '鲤鱼', '带鱼', '黄花鱼', '三文鱼', '虾', '基围虾', '大虾', '对虾', '明虾', '虾仁', '螃蟹', '蟹', '花甲', '蛤蜊', '扇贝', '生蚝', '鲍鱼', '海参', '鱿鱼', '墨鱼', '章鱼', '海蜇', '海带', '紫菜'],
    
    // 蛋奶类
    '蛋奶': ['鸡蛋', '鸭蛋', '鹅蛋', '鹌鹑蛋', '蛋黄', '蛋白', '牛奶', '纯牛奶', '酸奶', '淡奶油', '奶油', '奶油奶酪', '奶酪', '芝士', '黄油', '猪油', '炼乳', '咖啡伴侣', '厚乳'],
    
    // 主食类
    '主食': ['大米', '米饭', '燕麦米', '红糙米', '黑糯米', '糯米', '小米', '面条', '面饼', '挂面', '河粉', '鲜河粉', '米粉', '粉丝', '粉条', '饺子', '包子', '馒头', '面包', '吐司', '玉米', '玉米淀粉', '淀粉', '干淀粉', '面粉', '高筋面粉', '低筋面粉', '木薯粉'],
    
    // 调味品类
    '调味品': ['盐', '糖', '白砂糖', '冰糖', '红糖', '黑糖', '糖浆', '酱油', '生抽', '老抽', '味极鲜', '耗油', '蚝油', '料酒', '黄酒', '白米醋', '香醋', '陈醋', '白醋', '番茄酱', '豆瓣酱', '甜面酱', '黄豆酱', '芝麻酱', '花生酱', '辣椒酱', '蒜蓉酱', '十三香', '五香粉', '胡椒粉', '白胡椒粉', '黑胡椒粉', '孜然粉', '花椒', '花椒粒', '八角', '桂皮', '香叶', '草果', '干辣椒', '小苏打', '鸡精', '味精', '鸡粉', '话梅', '玫瑰', '绿茶', '红茶', '茶叶', '茶汤'],
    
    // 食用油类
    '食用油': ['食用油', '花生油', '菜籽油', '玉米油', '大豆油', '葵花籽油', '橄榄油', '芝麻油', '香油', '麻油', '色拉油'],
    
    // 其他
    '其他': ['水', '清水', '纯净水', '热水', '开水', '冰块', '小苏打', '泡打粉', '酵母', '可可粉', '巧克力', '黑巧克力', '红枣', '枸杞', '莲子', '百合', '银耳', '燕窝', '蜂蜜', '蜂王浆']
};

/**
 * 获取食材的分类
 * @param {string} ingredientName - 食材名称
 * @returns {string} 分类名称
 */
function getIngredientCategory(ingredientName) {
    // 移除可能的emoji和特殊字符
    const cleanName = ingredientName.replace(/[🥔🍆🥦🥬🥕🧄🧅🌶️🍅🥒🥑🍌🍎🍊🍋🍇🍓🍑🥭🍍🥝🍒🍈🍉🍐🍏🍋🍊🍌🍉🍇🍓🍒🍑🥭🍍🥝🍈🍐🍏🥑🥒🍅🌶️🧅🧄🥕🥬🥦🍆🥔]/g, '').trim();
    
    // 遍历所有分类
    for (const [category, keywords] of Object.entries(INGREDIENT_CATEGORIES)) {
        if (keywords.some(keyword => cleanName.includes(keyword) || keyword.includes(cleanName))) {
            return category;
        }
    }
    
    // 默认分类
    return '其他';
}

/**
 * 合并相同食材的数量
 * @param {Array} ingredients - 食材数组
 * @returns {Array} 合并后的食材数组
 */
function mergeIngredients(ingredients) {
    const merged = {};
    
    ingredients.forEach(ing => {
        const key = `${ing.name}_${ing.unit}`;
        
        if (merged[key]) {
            // 累加数量
            merged[key].quantity += ing.quantity;
            // 合并食谱来源（去重）
            if (ing.recipeId) {
                if (!merged[key].recipeIds) {
                    merged[key].recipeIds = [];
                }
                if (!merged[key].recipeIds.includes(ing.recipeId)) {
                    merged[key].recipeIds.push(ing.recipeId);
                }
            }
        } else {
            // 创建新条目
            merged[key] = {
                name: ing.name,
                quantity: ing.quantity,
                unit: ing.unit,
                category: getIngredientCategory(ing.name),
                purchased: ing.purchased || false,
                recipeIds: ing.recipeId ? [ing.recipeId] : []
            };
        }
    });
    
    return Object.values(merged);
}

/**
 * 从食谱ID列表收集食材
 * @param {Array} recipeIds - 食谱ID数组
 * @param {Array} allRecipes - 所有食谱数据
 * @returns {Array} 合并后的食材数组
 */
function collectIngredientsFromRecipes(recipeIds, allRecipes) {
    const allIngredients = [];
    
    recipeIds.forEach(recipeId => {
        const recipe = allRecipes.find(r => r.id === recipeId);
        if (recipe && recipe.ingredients) {
            recipe.ingredients.forEach(ing => {
                allIngredients.push({
                    name: ing.name,
                    quantity: ing.quantity,
                    unit: ing.unit,
                    recipeId: recipeId // 记录来源食谱ID
                });
            });
        }
    });
    
    return mergeIngredients(allIngredients);
}

/**
 * 按分类分组食材
 * @param {Array} ingredients - 食材数组
 * @returns {Object} 按分类分组的食材对象
 */
function groupIngredientsByCategory(ingredients) {
    const grouped = {};
    
    ingredients.forEach(ing => {
        const category = ing.category || '其他';
        if (!grouped[category]) {
            grouped[category] = [];
        }
        grouped[category].push(ing);
    });
    
    // 按分类名称排序
    const sortedCategories = Object.keys(grouped).sort();
    const sortedGrouped = {};
    sortedCategories.forEach(cat => {
        sortedGrouped[cat] = grouped[cat];
    });
    
    return sortedGrouped;
}

/**
 * 保存购物清单到 localStorage
 * @param {Array} ingredients - 食材数组
 * @param {Array} selectedRecipeIds - 选中的食谱ID数组
 */
function saveShoppingList(ingredients, selectedRecipeIds) {
    const data = {
        ingredients: ingredients,
        selectedRecipeIds: selectedRecipeIds,
        lastUpdated: new Date().toISOString()
    };
    localStorage.setItem('shoppingList', JSON.stringify(data));
}

/**
 * 从 localStorage 加载购物清单
 * @returns {Object} 购物清单数据
 */
function loadShoppingList() {
    const data = localStorage.getItem('shoppingList');
    if (data) {
        try {
            return JSON.parse(data);
        } catch (e) {
            console.error('加载购物清单失败:', e);
            return { ingredients: [], selectedRecipeIds: [] };
        }
    }
    return { ingredients: [], selectedRecipeIds: [] };
}

/**
 * 清空购物清单
 */
function clearShoppingList() {
    localStorage.removeItem('shoppingList');
}

/**
 * 更新食材的购买状态
 * @param {string} ingredientKey - 食材唯一标识 (name_unit)
 * @param {boolean} purchased - 是否已购买
 */
function updateIngredientPurchasedStatus(ingredientKey, purchased) {
    const data = loadShoppingList();
    const [name, unit] = ingredientKey.split('_');
    
    const ingredient = data.ingredients.find(ing => ing.name === name && ing.unit === unit);
    if (ingredient) {
        ingredient.purchased = purchased;
        saveShoppingList(data.ingredients, data.selectedRecipeIds);
    }
}

/**
 * 删除食材
 * @param {string} ingredientKey - 食材唯一标识 (name_unit)
 */
function removeIngredient(ingredientKey) {
    const data = loadShoppingList();
    const [name, unit] = ingredientKey.split('_');
    
    data.ingredients = data.ingredients.filter(ing => !(ing.name === name && ing.unit === unit));
    saveShoppingList(data.ingredients, data.selectedRecipeIds);
}

/**
 * 添加食谱到购物清单
 * @param {number} recipeId - 食谱ID
 * @param {Array} allRecipes - 所有食谱数据
 */
function addRecipeToShoppingList(recipeId, allRecipes) {
    const data = loadShoppingList();
    
    // 如果已经存在，不重复添加
    if (data.selectedRecipeIds.includes(recipeId)) {
        return;
    }
    
    // 添加食谱ID
    data.selectedRecipeIds.push(recipeId);
    
    // 重新收集所有食材
    const allIngredients = collectIngredientsFromRecipes(data.selectedRecipeIds, allRecipes);
    
    // 保留现有的购买状态和食谱来源
    allIngredients.forEach(ing => {
        const existing = data.ingredients.find(
            e => e.name === ing.name && e.unit === ing.unit
        );
        if (existing) {
            ing.purchased = existing.purchased;
            // 如果现有食材有食谱来源，合并它们
            if (existing.recipeIds && existing.recipeIds.length > 0) {
                // 合并并去重
                const combined = [...new Set([...(ing.recipeIds || []), ...existing.recipeIds])];
                ing.recipeIds = combined;
            }
        }
    });
    
    saveShoppingList(allIngredients, data.selectedRecipeIds);
}

/**
 * 从购物清单移除食谱
 * @param {number} recipeId - 食谱ID
 * @param {Array} allRecipes - 所有食谱数据
 */
function removeRecipeFromShoppingList(recipeId, allRecipes) {
    const data = loadShoppingList();
    
    // 移除食谱ID
    data.selectedRecipeIds = data.selectedRecipeIds.filter(id => id !== recipeId);
    
    // 重新收集剩余食谱的食材
    const allIngredients = collectIngredientsFromRecipes(data.selectedRecipeIds, allRecipes);
    
    // 保留现有的购买状态和食谱来源
    allIngredients.forEach(ing => {
        const existing = data.ingredients.find(
            e => e.name === ing.name && e.unit === ing.unit
        );
        if (existing) {
            ing.purchased = existing.purchased;
            // 如果现有食材有食谱来源，合并它们
            if (existing.recipeIds && existing.recipeIds.length > 0) {
                // 合并并去重
                const combined = [...new Set([...(ing.recipeIds || []), ...existing.recipeIds])];
                ing.recipeIds = combined;
            }
        }
    });
    
    saveShoppingList(allIngredients, data.selectedRecipeIds);
}

/**
 * 检查食谱是否在购物清单中
 * @param {number} recipeId - 食谱ID
 * @returns {boolean} 是否在购物清单中
 */
function isRecipeInShoppingList(recipeId) {
    const data = loadShoppingList();
    return data.selectedRecipeIds.includes(recipeId);
}

/**
 * 导出购物清单为JSON
 * @returns {string} JSON字符串
 */
function exportShoppingListToJSON() {
    const data = loadShoppingList();
    return JSON.stringify(data, null, 2);
}

/**
 * 获取购物清单统计信息
 * @returns {Object} 统计信息
 */
function getShoppingListStats() {
    const data = loadShoppingList();
    const total = data.ingredients.length;
    const purchased = data.ingredients.filter(ing => ing.purchased).length;
    const remaining = total - purchased;
    
    return {
        total,
        purchased,
        remaining,
        selectedRecipes: data.selectedRecipeIds.length
    };
}
