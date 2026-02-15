/**
 * 购物清单页面逻辑
 */

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否有分享数据，如果有则先加载分享数据，然后再加载页面
    const urlParams = new URLSearchParams(window.location.search);
    const shareData = urlParams.get('share');
    
    if (shareData) {
        // 有分享数据，先加载分享数据
        checkAndLoadSharedShoppingList();
    }
    
    // 加载购物清单页面（会在分享数据加载完成后自动触发重新渲染）
    loadShoppingListPage();
});

/**
 * 加载购物清单页面
 */
function loadShoppingListPage() {
    // 等待食谱数据加载
    if (typeof allRecipes === 'undefined' || !allRecipes || allRecipes.length === 0) {
        setTimeout(loadShoppingListPage, 100);
        return;
    }
    
    // 确保购物清单模块已加载
    if (typeof loadShoppingList === 'undefined' || typeof getShoppingListStats === 'undefined') {
        setTimeout(loadShoppingListPage, 100);
        return;
    }
    
    renderShoppingList();
    updateStats();
    renderShoppingListSidebar();
    renderShoppingNutritionSummary();
    
    // 调整侧边栏位置
    if (typeof adjustSidebarPosition === 'function') {
        setTimeout(adjustSidebarPosition, 100);
    }
}

/**
 * 渲染购物清单
 */
function renderShoppingList() {
    const container = document.getElementById('shopping-list-content');
    const emptyState = document.getElementById('shopping-list-empty');
    
    if (!container) {
        console.warn('shopping-list-content 容器未找到');
        return;
    }
    
    if (typeof loadShoppingList === 'undefined' || typeof groupIngredientsByCategory === 'undefined') {
        container.innerHTML = '<div class="loading">加载中...</div>';
        return;
    }
    
    const data = loadShoppingList();
    
    if (!data || !data.ingredients || data.ingredients.length === 0) {
        container.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }
    
    container.style.display = 'block';
    if (emptyState) emptyState.style.display = 'none';
    
    // 按分类分组
    const grouped = groupIngredientsByCategory(data.ingredients);
    
    // 渲染每个分类
    let html = '';
    for (const [category, ingredients] of Object.entries(grouped)) {
        html += `
            <div class="shopping-category" id="category-${category}">
                <h2 class="shopping-category-title">
                    <span class="category-icon">${getCategoryIcon(category)}</span>
                    ${category}
                    <span class="category-count">(${ingredients.length})</span>
                </h2>
                <ul class="shopping-ingredients-list">
                    ${ingredients.map(ing => renderIngredientItem(ing)).join('')}
                </ul>
            </div>
        `;
    }
    
    container.innerHTML = html;
    
    // 初始化滑动删除功能
    initSwipeToDelete();
}

/**
 * 渲染单个食材项
 */
function renderIngredientItem(ingredient) {
    const key = `${ingredient.name}_${ingredient.unit}`;
    const purchased = ingredient.purchased || false;
    
    // 获取食谱来源信息
    const recipeSources = getRecipeSources(ingredient.recipeIds || []);
    
    return `
        <li class="shopping-ingredient-item ${purchased ? 'purchased' : ''}" 
            data-ingredient-key="${key}">
            <div class="ingredient-item-content">
                <label class="ingredient-checkbox-label">
                    <input type="checkbox" 
                           class="ingredient-checkbox" 
                           ${purchased ? 'checked' : ''}
                           onchange="toggleIngredientPurchased('${key}', this.checked)">
                    <span class="checkbox-custom"></span>
                </label>
                <div class="ingredient-info">
                    <div class="ingredient-main-info">
                        <span class="ingredient-name">${ingredient.name}</span>
                        <span class="ingredient-quantity">
                            ${formatQuantity(ingredient.quantity)} ${ingredient.unit}
                        </span>
                    </div>
                    ${recipeSources.length > 0 ? `
                    <div class="ingredient-sources">
                        <span class="sources-label">来自：</span>
                        <div class="sources-list">
                            ${recipeSources.map(recipe => `
                                <a href="recipe_detail.html?id=${recipe.id}" 
                                   class="source-recipe-tag" 
                                   title="${recipe.title}"
                                   onclick="event.stopPropagation()">
                                    ${recipe.title}
                                </a>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                </div>
            </div>
            <div class="ingredient-delete-action" 
                 onclick="handleSwipeRemovePurchased('${key}', this.closest('.shopping-ingredient-item'))">
                <span class="delete-icon">${purchased ? '↩️' : '✓'}</span>
                <span class="delete-text">${purchased ? '移除已购' : '标记已购'}</span>
            </div>
        </li>
    `;
}

/**
 * 获取食谱来源信息
 * @param {Array} recipeIds - 食谱ID数组
 * @returns {Array} 食谱信息数组
 */
function getRecipeSources(recipeIds) {
    // 从全局 allRecipes 获取
    const recipes = typeof allRecipes !== 'undefined' ? allRecipes : [];
    
    if (!recipes || recipes.length === 0) {
        return [];
    }
    
    return recipeIds
        .map(id => recipes.find(r => r.id === id))
        .filter(recipe => recipe !== undefined)
        .map(recipe => ({
            id: recipe.id,
            title: recipe.title
        }));
}

/**
 * 格式化数量显示
 */
function formatQuantity(quantity) {
    // 如果是整数，不显示小数
    if (quantity % 1 === 0) {
        return quantity.toString();
    }
    // 否则保留1位小数
    return quantity.toFixed(1);
}

/**
 * 获取分类图标
 */
function getCategoryIcon(category) {
    const icons = {
        '蔬菜': '🥬',
        '水果': '🍎',
        '肉类': '🥩',
        '海鲜': '🦐',
        '蛋奶': '🥛',
        '主食': '🍚',
        '调味品': '🧂',
        '食用油': '🫒',
        '其他': '📦'
    };
    return icons[category] || '📦';
}

/**
 * 切换食材购买状态
 */
function toggleIngredientPurchased(ingredientKey, purchased) {
    updateIngredientPurchasedStatus(ingredientKey, purchased);
    renderShoppingList();
    updateStats();
    renderShoppingListSidebar();
}

/**
 * 从清单中删除食材
 */
function removeIngredientFromList(ingredientKey) {
    if (confirm('确定要删除这个食材吗？')) {
        removeIngredient(ingredientKey);
        renderShoppingList();
        updateStats();
        renderShoppingListSidebar();
    }
}

/**
 * 更新统计信息
 */
function updateStats() {
    if (typeof getShoppingListStats === 'undefined') {
        console.error('getShoppingListStats 函数未定义');
        return;
    }
    
    try {
        const stats = getShoppingListStats();
        
        const totalEl = document.getElementById('stat-total');
        const purchasedEl = document.getElementById('stat-purchased');
        const remainingEl = document.getElementById('stat-remaining');
        const recipesEl = document.getElementById('stat-recipes');
        
        if (totalEl) totalEl.textContent = stats.total || 0;
        if (purchasedEl) purchasedEl.textContent = stats.purchased || 0;
        if (remainingEl) remainingEl.textContent = stats.remaining || 0;
        if (recipesEl) recipesEl.textContent = stats.selectedRecipes || 0;
    } catch (error) {
        console.error('更新统计信息失败:', error);
    }
}

/**
 * 清空整个购物清单
 */
function clearAllShoppingList() {
    if (confirm('确定要清空整个购物清单吗？此操作不可恢复。')) {
        clearShoppingList();
        renderShoppingList();
        updateStats();
        renderShoppingListSidebar();
    }
}

/**
 * 导出购物清单为JSON文件
 */
function exportShoppingList() {
    const json = exportShoppingListToJSON();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `shopping_list_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * 渲染购物清单侧边栏
 */
function renderShoppingListSidebar() {
    renderShoppingListTOC();
    renderSelectedRecipesList();
    renderShoppingStatsSidebar();
    renderShoppingNutritionSummary();
}

/**
 * 渲染购物清单营养总汇（按已选食谱 & 分量比例汇总）
 */
function renderShoppingNutritionSummary() {
    const container = document.getElementById('shopping-nutrition-summary');
    if (!container) return;

    if (typeof loadShoppingList !== 'function' || typeof allRecipes === 'undefined' || !allRecipes) {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">加载中...</p>';
        return;
    }

    const data = loadShoppingList();
    const hasRecipes = data && Array.isArray(data.selectedRecipeIds) && data.selectedRecipeIds.length > 0;

    const utils = (typeof NutritionUtils !== 'undefined') ? NutritionUtils : null;
    if (!utils || typeof utils.sumNutritionForShoppingList !== 'function') {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">营养模块未加载</p>';
        return;
    }

    const totals = hasRecipes ? utils.sumNutritionForShoppingList(data, allRecipes) : utils.emptyTotals();

    container.innerHTML = `
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🔥 热量</span>
            <span class="nutrition-summary-value">${Math.round(totals.calories)} 千卡</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🥩 蛋白质</span>
            <span class="nutrition-summary-value">${totals.protein.toFixed(1)} 克</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🍞 碳水</span>
            <span class="nutrition-summary-value">${totals.carbs.toFixed(1)} 克</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🧈 脂肪</span>
            <span class="nutrition-summary-value">${totals.fat.toFixed(1)} 克</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🧂 盐</span>
            <span class="nutrition-summary-value">${totals.salt.toFixed(2)} 克</span>
        </div>
        ${hasRecipes ? '' : '<p style="margin-top: var(--spacing-3); color: var(--text-tertiary); font-size: var(--text-sm);">清单为空时显示为 0</p>'}
    `;
}

/**
 * 渲染分类导航
 */
function renderShoppingListTOC() {
    const container = document.getElementById('shopping-list-toc');
    if (!container) {
        console.warn('shopping-list-toc 容器未找到');
        return;
    }
    
    if (typeof loadShoppingList === 'undefined' || typeof groupIngredientsByCategory === 'undefined') {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">加载中...</p>';
        return;
    }
    
    const data = loadShoppingList();
    if (!data || !data.ingredients || data.ingredients.length === 0) {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">暂无食材</p>';
        return;
    }
    
    // 按分类分组
    const grouped = groupIngredientsByCategory(data.ingredients);
    const categories = Object.keys(grouped);
    
    if (categories.length === 0) {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">暂无分类</p>';
        return;
    }
    
    container.innerHTML = categories.map(category => {
        const count = grouped[category].length;
        const purchasedCount = grouped[category].filter(ing => ing.purchased).length;
        return `
            <a href="#category-${category}" 
               class="toc-item" 
               onclick="scrollToCategory('${category}'); return false;">
                <span class="toc-icon">${getCategoryIcon(category)}</span>
                <span class="toc-label">${category}</span>
                <span class="toc-count">${purchasedCount}/${count}</span>
            </a>
        `;
    }).join('');
}

/**
 * 滚动到指定分类
 */
function scrollToCategory(category) {
    const categoryElement = document.getElementById(`category-${category}`);
    if (categoryElement) {
        categoryElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // 添加高亮效果
        categoryElement.style.transition = 'background-color 0.3s ease';
        categoryElement.style.backgroundColor = 'var(--primary-bg)';
        setTimeout(() => {
            categoryElement.style.backgroundColor = '';
        }, 2000);
    }
}

/**
 * 渲染已选食谱列表
 */
function renderSelectedRecipesList() {
    const container = document.getElementById('selected-recipes-list');
    if (!container) {
        console.warn('selected-recipes-list 容器未找到');
        return;
    }
    
    if (typeof loadShoppingList === 'undefined') {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">加载中...</p>';
        return;
    }
    
    if (typeof allRecipes === 'undefined' || !allRecipes || allRecipes.length === 0) {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">等待数据加载...</p>';
        return;
    }
    
    const data = loadShoppingList();
    if (!data || !data.selectedRecipeIds || data.selectedRecipeIds.length === 0) {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">暂无已选食谱</p>';
        return;
    }
    
    const selectedRecipes = data.selectedRecipeIds
        .map(id => allRecipes.find(r => r.id === id))
        .filter(recipe => recipe !== undefined);
    
    if (selectedRecipes.length === 0) {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">暂无已选食谱</p>';
        return;
    }
    
    const recipeScales = (data && data.recipeScales) ? data.recipeScales : {};

    container.innerHTML = selectedRecipes.map(recipe => {
        const scale = recipeScales && recipeScales[recipe.id] !== undefined ? Number(recipeScales[recipe.id]) : 1;
        const scaleText = (Number.isFinite(scale) && scale !== 1) ? ` (x${scale.toFixed(2)})` : '';
        const fullTitle = `${recipe.title}${scaleText}`;
        const imageUrl = recipe.imageUrl || '';
        return `
            <div class="selected-recipe-item">
                ${imageUrl ? `
                <a href="recipe_detail.html?id=${recipe.id}" 
                   class="selected-recipe-image-link"
                   title="${fullTitle}">
                    <img src="${imageUrl}" 
                         alt="${recipe.title}" 
                         class="selected-recipe-image"
                         onerror="this.style.display='none'; this.parentElement.innerHTML='<div class=\\'selected-recipe-image-placeholder\\'>🍽️</div>';">
                </a>
                ` : `
                <div class="selected-recipe-image-placeholder">🍽️</div>
                `}
                <div class="selected-recipe-content">
                    <a href="recipe_detail.html?id=${recipe.id}" 
                       class="selected-recipe-link"
                       title="${fullTitle}">
                        <span class="recipe-title">${fullTitle}</span>
                    </a>
                    <div class="selected-recipe-actions">
                        <label class="recipe-scale-editor" title="调整分量比例">
                            <span class="scale-label">x</span>
                            <input class="recipe-scale-input"
                                   type="number"
                                   step="0.1"
                                   min="0.1"
                                   max="20"
                                   value="${Number.isFinite(scale) ? scale : 1}"
                                   onchange="updateSelectedRecipeScale(${recipe.id}, this.value); event.stopPropagation();">
                        </label>
                        <button class="remove-recipe-btn" 
                                onclick="removeRecipeFromShoppingListPage(${recipe.id}); return false;"
                                title="移除">
                            <span>✕</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 更新已选食谱的分量比例（购物清单页）
 */
function updateSelectedRecipeScale(recipeId, scale) {
    if (typeof updateRecipeScaleInShoppingList !== 'function') {
        console.error('updateRecipeScaleInShoppingList 未定义');
        return;
    }
    updateRecipeScaleInShoppingList(recipeId, scale, allRecipes);
    renderShoppingList();
    updateStats();
    renderShoppingListSidebar();
}
/**
 * 从购物清单移除食谱（页面版本）
 */
function removeRecipeFromShoppingListPage(recipeId) {
    if (confirm('确定要从购物清单中移除这个食谱吗？')) {
        removeRecipeFromShoppingList(recipeId, allRecipes);
        renderShoppingList();
        updateStats();
        renderShoppingListSidebar();
    }
}

/**
 * 渲染侧边栏统计信息
 */
function renderShoppingStatsSidebar() {
    const container = document.getElementById('shopping-stats-sidebar');
    if (!container) {
        console.warn('shopping-stats-sidebar 容器未找到');
        return;
    }
    
    if (typeof getShoppingListStats === 'undefined' || typeof loadShoppingList === 'undefined') {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">加载中...</p>';
        return;
    }
    
    const stats = getShoppingListStats();
    const data = loadShoppingList();
    
    if (!data || !data.ingredients) {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">暂无数据</p>';
        return;
    }
    
    // 按分类统计
    let categoryStats = [];
    if (typeof groupIngredientsByCategory !== 'undefined' && data.ingredients.length > 0) {
        const grouped = groupIngredientsByCategory(data.ingredients);
        categoryStats = Object.entries(grouped).map(([category, ingredients]) => {
            const total = ingredients.length;
            const purchased = ingredients.filter(ing => ing.purchased).length;
            return { category, total, purchased };
        });
    }
    
    let html = `
        <div class="stats-sidebar-item">
            <div class="stats-sidebar-label">总食材数</div>
            <div class="stats-sidebar-value">${stats.total || 0}</div>
        </div>
        <div class="stats-sidebar-item">
            <div class="stats-sidebar-label">已购买</div>
            <div class="stats-sidebar-value">${stats.purchased || 0}</div>
        </div>
        <div class="stats-sidebar-item">
            <div class="stats-sidebar-label">待购买</div>
            <div class="stats-sidebar-value">${stats.remaining || 0}</div>
        </div>
        <div class="stats-sidebar-item">
            <div class="stats-sidebar-label">已选食谱</div>
            <div class="stats-sidebar-value">${stats.selectedRecipes || 0}</div>
        </div>
    `;
    
    if (categoryStats.length > 0) {
        html += '<div class="stats-sidebar-divider"></div>';
        html += '<div class="stats-sidebar-categories">';
        categoryStats.forEach(({ category, total, purchased }) => {
            const progress = total > 0 ? (purchased / total * 100).toFixed(0) : 0;
            html += `
                <div class="stats-category-item">
                    <div class="stats-category-header">
                        <span class="stats-category-icon">${getCategoryIcon(category)}</span>
                        <span class="stats-category-name">${category}</span>
                        <span class="stats-category-count">${purchased}/${total}</span>
                    </div>
                    <div class="stats-category-progress">
                        <div class="stats-category-progress-bar" style="width: ${progress}%"></div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
    }
    
    container.innerHTML = html;
}

/**
 * 标记所有食材为已购买
 */
function markAllPurchased() {
    const data = loadShoppingList();
    data.ingredients.forEach(ing => {
        ing.purchased = true;
    });
    saveShoppingList(data.ingredients, data.selectedRecipeIds, data.recipeScales);
    renderShoppingList();
    updateStats();
    renderShoppingListSidebar();
}

/**
 * 重置所有食材的购买状态
 */
function markAllUnpurchased() {
    const data = loadShoppingList();
    data.ingredients.forEach(ing => {
        ing.purchased = false;
    });
    saveShoppingList(data.ingredients, data.selectedRecipeIds, data.recipeScales);
    renderShoppingList();
    updateStats();
    renderShoppingListSidebar();
}

/**
 * 分享购物清单
 * 将购物清单数据编码到 URL 并复制到剪贴板
 */
function shareShoppingList() {
    const data = loadShoppingList();
    
    // 检查是否有数据可分享
    if (!data || !data.selectedRecipeIds || data.selectedRecipeIds.length === 0) {
        showShareToast('购物清单为空，无法分享', 'error');
        return;
    }
    
    try {
        // 准备分享数据（使用紧凑格式）
        // 食谱：[[id, scale], ...] 而不是 [{id, scale}, ...]
        const recipes = data.selectedRecipeIds.map(id => [
            id,
            data.recipeScales && data.recipeScales[id] ? data.recipeScales[id] : 1
        ]);
        
        // 食材：[[name, quantity, unit, purchased], ...] 而不是 [{name, quantity, unit, purchased}, ...]
        const ingredients = data.ingredients.map(ing => [
            ing.name,
            ing.quantity,
            ing.unit,
            ing.purchased || false
        ]);
        
        // 使用紧凑的数组格式
        const shareData = [recipes, ingredients];
        
        // 将数据编码为 JSON 字符串
        const jsonString = JSON.stringify(shareData);
        
        // 使用 LZ-string 压缩（如果可用），否则使用 Base64
        let encoded;
        if (typeof LZString !== 'undefined') {
            // LZ-string 压缩，然后进行 Base64URL 编码（URL 安全）
            const compressed = LZString.compressToBase64(jsonString);
            encoded = compressed;
        } else {
            // 降级方案：使用 Base64 编码
            encoded = btoa(encodeURIComponent(jsonString));
        }
        
        // 构建分享 URL
        const currentUrl = new URL(window.location.href);
        currentUrl.searchParams.set('share', encoded);
        const shareUrl = currentUrl.toString();
        
        // 复制到剪贴板
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(shareUrl).then(() => {
                showShareToast('分享链接已复制到剪贴板', 'success');
            }).catch(err => {
                console.error('复制失败:', err);
                // 降级方案：使用传统方法
                fallbackCopyToClipboard(shareUrl);
            });
        } else {
            // 降级方案：使用传统方法
            fallbackCopyToClipboard(shareUrl);
        }
    } catch (error) {
        console.error('分享失败:', error);
        showShareToast('分享失败，请重试', 'error');
    }
}

/**
 * 降级方案：使用传统方法复制到剪贴板
 */
function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        const successful = document.execCommand('copy');
        if (successful) {
            showShareToast('分享链接已复制到剪贴板', 'success');
        } else {
            showShareToast('复制失败，请手动复制链接', 'error');
        }
    } catch (err) {
        console.error('复制失败:', err);
        showShareToast('复制失败，请手动复制链接', 'error');
    } finally {
        document.body.removeChild(textArea);
    }
}

/**
 * 显示分享提示消息
 */
function showShareToast(message, type = 'success') {
    // 移除已存在的提示
    const existingToast = document.querySelector('.share-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 创建新的提示元素
    const toast = document.createElement('div');
    toast.className = `share-toast share-toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // 触发显示动画
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });
    
    // 3秒后自动隐藏
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

/**
 * 检查并加载分享的购物清单
 */
function checkAndLoadSharedShoppingList() {
    const urlParams = new URLSearchParams(window.location.search);
    const shareData = urlParams.get('share');
    
    if (!shareData) {
        return; // 没有分享数据，正常加载
    }
    
    try {
        // 解码数据（支持 LZ-string 压缩和 Base64）
        let decoded;
        if (typeof LZString !== 'undefined') {
            try {
                // 尝试使用 LZ-string 解压
                decoded = LZString.decompressFromBase64(shareData);
                if (!decoded) {
                    // 如果解压失败，尝试 Base64 解码（兼容旧格式）
                    decoded = decodeURIComponent(atob(shareData));
                }
            } catch (e) {
                // 如果出错，使用 Base64 解码（兼容旧格式）
                decoded = decodeURIComponent(atob(shareData));
            }
        } else {
            // 降级方案：使用 Base64 解码
            decoded = decodeURIComponent(atob(shareData));
        }
        
        const parsed = JSON.parse(decoded);
        
        // 支持新旧两种格式
        let recipes, ingredients;
        if (Array.isArray(parsed) && parsed.length === 2) {
            // 新格式：紧凑数组 [[recipes], [ingredients]]
            recipes = parsed[0];
            ingredients = parsed[1];
        } else if (parsed.recipes && Array.isArray(parsed.recipes)) {
            // 旧格式：对象 {recipes: [...], ingredients: [...]}
            recipes = parsed.recipes;
            ingredients = parsed.ingredients;
        } else {
            console.warn('分享数据格式无效');
            showShareToast('分享链接无效', 'error');
            clearShareUrl();
            return;
        }
        
        if (!recipes || recipes.length === 0) {
            console.warn('分享数据中没有食谱');
            showShareToast('分享链接无效', 'error');
            clearShareUrl();
            return;
        }
        
        // 检查是否已加载食谱数据
        if (typeof allRecipes === 'undefined' || !allRecipes || allRecipes.length === 0) {
            // 等待食谱数据加载
            setTimeout(checkAndLoadSharedShoppingList, 100);
            return;
        }
        
        // 解析食谱数据（支持新旧格式）
        const recipeList = recipes.map(r => {
            if (Array.isArray(r)) {
                // 新格式：[id, scale]
                return { id: r[0], scale: r[1] || 1 };
            } else {
                // 旧格式：{id, scale}
                return { id: r.id, scale: r.scale || 1 };
            }
        });
        
        // 验证食谱是否存在
        const validRecipes = recipeList.filter(r => {
            const recipe = allRecipes.find(rec => rec.id === r.id);
            return recipe !== undefined;
        });
        
        if (validRecipes.length === 0) {
            showShareToast('分享的食谱不存在', 'error');
            clearShareUrl();
            return;
        }
        
        // 构建购物清单数据
        const selectedRecipeIds = validRecipes.map(r => r.id);
        const recipeScales = {};
        validRecipes.forEach(r => {
            recipeScales[r.id] = normalizeScale(r.scale || 1);
        });
        
        // 如果有食材数据，使用分享的食材（保留购买状态）
        // 否则从食谱重新收集
        let finalIngredients;
        if (ingredients && Array.isArray(ingredients) && ingredients.length > 0) {
            // 解析食材数据（支持新旧格式）
            const ingredientList = ingredients.map(ing => {
                if (Array.isArray(ing)) {
                    // 新格式：[name, quantity, unit, purchased]
                    return {
                        name: ing[0],
                        quantity: ing[1],
                        unit: ing[2],
                        purchased: ing[3] || false
                    };
                } else {
                    // 旧格式：{name, quantity, unit, purchased}
                    return {
                        name: ing.name,
                        quantity: ing.quantity,
                        unit: ing.unit,
                        purchased: ing.purchased || false
                    };
                }
            });
            
            // 使用分享的食材数据，但需要重新收集以确保数量正确（考虑分量比例）
            const collectedIngredients = collectIngredientsFromRecipes(selectedRecipeIds, allRecipes, recipeScales);
            
            // 合并分享的购买状态
            collectedIngredients.forEach(ing => {
                const sharedIng = ingredientList.find(
                    si => si.name === ing.name && si.unit === ing.unit
                );
                if (sharedIng) {
                    ing.purchased = sharedIng.purchased || false;
                }
            });
            
            finalIngredients = collectedIngredients;
        } else {
            // 从食谱重新收集
            finalIngredients = collectIngredientsFromRecipes(selectedRecipeIds, allRecipes, recipeScales);
        }
        
        // 保存到购物清单
        saveShoppingList(finalIngredients, selectedRecipeIds, recipeScales);
        
        // 显示成功提示
        showShareToast(`已加载 ${validRecipes.length} 个食谱的购物清单`, 'success');
        
        // 清除 URL 参数，避免刷新时重复加载
        clearShareUrl();
        
        // 重新渲染页面以显示加载的分享数据
        if (typeof renderShoppingList === 'function') {
            renderShoppingList();
            updateStats();
            renderShoppingListSidebar();
            renderShoppingNutritionSummary();
        }
        
    } catch (error) {
        console.error('解析分享数据失败:', error);
        showShareToast('分享链接无效或已损坏', 'error');
        clearShareUrl();
    }
}

/**
 * 清除 URL 中的分享参数
 */
function clearShareUrl() {
    const url = new URL(window.location.href);
    url.searchParams.delete('share');
    window.history.replaceState({}, '', url.toString());
}

/**
 * 初始化滑动删除功能（移动端）
 */
function initSwipeToDelete() {
    // 只在移动端启用
    if (window.innerWidth > 768) {
        return;
    }
    
    const items = document.querySelectorAll('.shopping-ingredient-item');
    
    items.forEach(item => {
        let touchStartX = 0;
        let touchStartY = 0;
        let isSwiping = false;
        let currentX = 0;
        let startTime = 0;
        
        const content = item.querySelector('.ingredient-item-content');
        const deleteAction = item.querySelector('.ingredient-delete-action');
        
        if (!content || !deleteAction) return;
        
        // 触摸开始
        item.addEventListener('touchstart', (e) => {
            if (e.touches.length !== 1) return;
            
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
            startTime = Date.now();
            isSwiping = false;
            currentX = 0;
        }, { passive: true });
        
        // 触摸移动
        item.addEventListener('touchmove', (e) => {
            if (e.touches.length !== 1) return;
            
            const touchX = e.touches[0].clientX;
            const touchY = e.touches[0].clientY;
            
            const deltaX = touchX - touchStartX;
            const deltaY = touchY - touchStartY;
            
            // 判断是否为水平滑动
            if (!isSwiping && Math.abs(deltaX) > 10 && Math.abs(deltaX) > Math.abs(deltaY)) {
                isSwiping = true;
            }
            
            if (isSwiping) {
                e.preventDefault();
                
                // 只允许向左滑动
                if (deltaX < 0) {
                    currentX = Math.max(deltaX, -100);
                    content.style.transform = `translateX(${currentX}px)`;
                    deleteAction.style.opacity = Math.min(Math.abs(currentX) / 100, 1).toString();
                }
            }
        }, { passive: false });
        
        // 触摸结束
        item.addEventListener('touchend', () => {
            if (!isSwiping) return;
            
            // 如果滑动超过阈值，执行操作
            if (currentX < -50) {
                item.classList.add('swiped-open');
                content.style.transform = 'translateX(-100px)';
                deleteAction.style.opacity = '1';
                
                // 执行移除已购操作
                const ingredientKey = item.getAttribute('data-ingredient-key');
                if (ingredientKey) {
                    handleSwipeRemovePurchased(ingredientKey, item);
                }
            } else {
                // 恢复原状
                item.classList.remove('swiped-open');
                content.style.transform = '';
                deleteAction.style.opacity = '0';
            }
            
            isSwiping = false;
            currentX = 0;
        }, { passive: true });
        
        // 触摸取消
        item.addEventListener('touchcancel', () => {
            if (isSwiping) {
                item.classList.remove('swiped-open');
                content.style.transform = '';
                deleteAction.style.opacity = '0';
            }
            isSwiping = false;
            currentX = 0;
        }, { passive: true });
        
        // 点击删除区域
        deleteAction.addEventListener('click', (e) => {
            e.stopPropagation();
            const ingredientKey = item.getAttribute('data-ingredient-key');
            if (ingredientKey) {
                handleSwipeRemovePurchased(ingredientKey, item);
            }
        });
    });
}

/**
 * 处理滑动移除已购食材
 */
function handleSwipeRemovePurchased(ingredientKey, itemElement) {
    const data = loadShoppingList();
    const ingredient = data.ingredients.find(ing => {
        const key = `${ing.name}_${ing.unit}`;
        return key === ingredientKey;
    });
    
    if (!ingredient) return;
    
    // 保存移除前的状态（用于撤回）
    const undoData = {
        ingredientKey: ingredientKey,
        wasPurchased: ingredient.purchased || false,
        timestamp: Date.now()
    };
    
    // 如果已购买，则移除（标记为未购买）
    if (ingredient.purchased) {
        ingredient.purchased = false;
        saveShoppingList(data.ingredients, data.selectedRecipeIds, data.recipeScales);
        
        // 显示撤回提示
        showUndoToast(ingredient.name, undoData);
        
        // 重新渲染
        renderShoppingList();
        updateStats();
        renderShoppingListSidebar();
    } else {
        // 如果未购买，则标记为已购买
        ingredient.purchased = true;
        saveShoppingList(data.ingredients, data.selectedRecipeIds, data.recipeScales);
        
        // 显示撤回提示
        showUndoToast(ingredient.name, undoData);
        
        // 重新渲染
        renderShoppingList();
        updateStats();
        renderShoppingListSidebar();
    }
    
    // 恢复卡片状态
    itemElement.classList.remove('swiped-open');
    const content = itemElement.querySelector('.ingredient-item-content');
    if (content) {
        content.style.transform = '';
    }
    const deleteAction = itemElement.querySelector('.ingredient-delete-action');
    if (deleteAction) {
        deleteAction.style.opacity = '0';
    }
}

/**
 * 显示撤回提示
 */
let undoTimeout = null;
let currentUndoData = null;

function showUndoToast(ingredientName, undoData) {
    // 清除之前的提示
    const existingToast = document.getElementById('undo-toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 清除之前的定时器
    if (undoTimeout) {
        clearTimeout(undoTimeout);
    }
    
    // 保存撤回数据
    currentUndoData = undoData;
    
    // 创建提示元素
    const toast = document.createElement('div');
    toast.id = 'undo-toast';
    toast.className = 'undo-toast';
    toast.innerHTML = `
        <span class="undo-toast-text">${ingredientName} 已${undoData.wasPurchased ? '移除' : '标记为已购'}</span>
        <button class="undo-toast-btn" onclick="undoRemovePurchased()" aria-label="撤回">
            <img src="images/撤回小猫.png" alt="撤回" class="undo-icon">
        </button>
    `;
    
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 5秒后自动隐藏
    undoTimeout = setTimeout(() => {
        hideUndoToast();
    }, 5000);
}

/**
 * 隐藏撤回提示
 */
function hideUndoToast() {
    const toast = document.getElementById('undo-toast');
    if (toast) {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }
    currentUndoData = null;
    if (undoTimeout) {
        clearTimeout(undoTimeout);
        undoTimeout = null;
    }
}

/**
 * 撤回移除操作
 */
function undoRemovePurchased() {
    if (!currentUndoData) return;
    
    const data = loadShoppingList();
    const ingredient = data.ingredients.find(ing => {
        const key = `${ing.name}_${ing.unit}`;
        return key === currentUndoData.ingredientKey;
    });
    
    if (ingredient) {
        // 恢复之前的状态
        ingredient.purchased = currentUndoData.wasPurchased;
        saveShoppingList(data.ingredients, data.selectedRecipeIds, data.recipeScales);
        
        // 重新渲染
        renderShoppingList();
        updateStats();
        renderShoppingListSidebar();
    }
    
    // 隐藏提示
    hideUndoToast();
}
