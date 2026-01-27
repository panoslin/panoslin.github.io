/**
 * 食谱管理系统 - 主JavaScript文件
 * 负责数据加载、搜索、筛选和页面渲染
 */

// 切换食谱在购物清单中的状态
function toggleRecipeInShoppingList(recipeId) {
    if (typeof addRecipeToShoppingList === 'undefined' || typeof removeRecipeFromShoppingList === 'undefined') {
        console.error('购物清单模块未加载');
        return;
    }
    
    const isInList = isRecipeInShoppingList(recipeId);
    
    if (isInList) {
        removeRecipeFromShoppingList(recipeId, allRecipes);
    } else {
        addRecipeToShoppingList(recipeId, allRecipes);
    }
    
    // 只更新对应卡片的状态，而不是重新渲染整个列表
    updateRecipeCardShoppingButton(recipeId);
    
    // 更新购物清单按钮状态（如果存在）
    updateShoppingListButton();
}

// 更新单个食谱卡片的购物清单按钮状态
function updateRecipeCardShoppingButton(recipeId) {
    // 通过按钮的 data-recipe-id 或卡片的 data-recipe-id 查找
    const button = document.querySelector(`.add-to-shopping-list-btn[data-recipe-id="${recipeId}"]`) ||
                   document.querySelector(`.recipe-card[data-recipe-id="${recipeId}"] .add-to-shopping-list-btn`);
    
    if (!button) {
        // 如果找不到，尝试通过按钮的 onclick 属性查找
        const allButtons = document.querySelectorAll('.add-to-shopping-list-btn');
        for (const btn of allButtons) {
            if (btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(`toggleRecipeInShoppingList(${recipeId})`)) {
                updateButtonState(btn, recipeId);
                return;
            }
        }
        return;
    }
    
    updateButtonState(button, recipeId);
}

// 更新按钮状态的辅助函数
function updateButtonState(button, recipeId) {
    const isInList = typeof isRecipeInShoppingList !== 'undefined' && isRecipeInShoppingList(recipeId);
    const btnIcon = button.querySelector('.btn-icon');
    const btnText = button.querySelector('.btn-text');
    
    if (isInList) {
        button.classList.add('added');
        button.title = '已添加到购物清单';
        if (btnIcon) btnIcon.textContent = '✓';
        if (btnText) btnText.textContent = '已添加';
    } else {
        button.classList.remove('added');
        button.title = '添加到购物清单';
        if (btnIcon) btnIcon.textContent = '🛒';
        if (btnText) btnText.textContent = '加入清单';
    }
}

// 更新购物清单按钮状态
function updateShoppingListButton() {
    if (typeof getShoppingListStats === 'undefined') return;
    
    const stats = getShoppingListStats();
    const btn = document.getElementById('shopping-list-btn');
    if (btn) {
        const badge = btn.querySelector('.shopping-list-badge');
        if (badge) {
            badge.textContent = stats.selectedRecipes > 0 ? stats.selectedRecipes : '';
            badge.style.display = stats.selectedRecipes > 0 ? 'flex' : 'none';
        }
    }
}

// 全局变量
let allRecipes = [];
let filteredRecipes = [];
let currentCategory = 'all';

/**
 * 页面加载完成后初始化
 */
document.addEventListener('DOMContentLoaded', function() {
    loadRecipes();
    initializeEventListeners();
    initializeLazyLoading();
    adjustSidebarPosition(); // 调整侧边栏位置
    initializeHeaderScroll(); // 初始化 Header 滚动收缩功能
});

/**
 * 调整侧边栏位置，确保不被header遮挡
 */
function adjustSidebarPosition() {
    const header = document.querySelector('.header');
    const sidebars = document.querySelectorAll('.sidebar');
    
    if (header && sidebars.length > 0) {
        // 获取header的实际高度
        const headerHeight = header.offsetHeight;
        
        // 为每个侧边栏设置top值，添加额外间距
        sidebars.forEach(sidebar => {
            sidebar.style.top = `${headerHeight + 16}px`; // header高度 + 16px间距
            sidebar.style.maxHeight = `calc(100vh - ${headerHeight + 64}px)`; // 调整最大高度
        });
    }
}

// 监听窗口大小变化，重新调整
window.addEventListener('resize', adjustSidebarPosition);

/**
 * 从JSON文件加载食谱数据
 */
async function loadRecipes() {
    try {
        const response = await fetch('recipes.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        allRecipes = await response.json();
        filteredRecipes = allRecipes;
        
        // 根据当前页面渲染内容
        if (document.getElementById('recipes-grid')) {
            renderRecipes(filteredRecipes);
            renderCategoryFilters();
            renderSidebarContent(); // 渲染侧边栏内容
        } else if (document.getElementById('recipe-detail')) {
            loadRecipeDetail();
        } else if (document.getElementById('shopping-list-content')) {
            // 购物清单页面
            if (typeof loadShoppingListPage === 'function') {
                loadShoppingListPage();
            }
        }
    } catch (error) {
        console.error('加载食谱数据失败:', error);
        showError('无法加载食谱数据，请检查recipes.json文件是否存在。');
    }
}

/**
 * 初始化事件监听器
 */
function initializeEventListeners() {
    // 搜索功能
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
    }
    
    // 分类筛选
    const categoryButtons = document.querySelectorAll('.category-btn');
    categoryButtons.forEach(btn => {
        btn.addEventListener('click', handleCategoryFilter);
    });
}

/**
 * 处理搜索输入
 */
function handleSearch(event) {
    const searchTerm = event.target.value.toLowerCase().trim();
    
    if (searchTerm === '') {
        // 如果搜索框为空，显示当前分类的所有食谱
        filterByCategory(currentCategory);
    } else {
        // 执行搜索
        performSearch(searchTerm);
    }
}

/**
 * 执行搜索功能
 * @param {string} searchTerm - 搜索关键词
 */
function performSearch(searchTerm) {
    filteredRecipes = allRecipes.filter(recipe => {
        // 搜索标题
        const titleMatch = recipe.title.toLowerCase().includes(searchTerm);
        
        // 搜索描述
        const descMatch = recipe.description && 
            recipe.description.toLowerCase().includes(searchTerm);
        
        // 搜索食材
        const ingredientsMatch = recipe.ingredients.some(ingredient =>
            ingredient.name.toLowerCase().includes(searchTerm)
        );
        
        // 搜索制作方法
        const instructionsMatch = recipe.instructions.some(instruction =>
            instruction.toLowerCase().includes(searchTerm)
        );
        
        // 搜索分类
        const categoryMatch = recipe.category.some(cat =>
            cat.toLowerCase().includes(searchTerm)
        );
        
        return titleMatch || descMatch || ingredientsMatch || 
               instructionsMatch || categoryMatch;
    });
    
    renderRecipes(filteredRecipes, searchTerm);
}

/**
 * 处理分类筛选
 */
function handleCategoryFilter(event) {
    const category = event.target.dataset.category;
    currentCategory = category;
    
    // 更新按钮状态
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // 清空搜索框
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = '';
    }
    
    // 筛选食谱
    filterByCategory(category);
}

/**
 * 按分类筛选食谱
 * @param {string} category - 分类名称，'all'表示显示所有
 */
function filterByCategory(category) {
    if (category === 'all') {
        filteredRecipes = allRecipes;
    } else {
        filteredRecipes = allRecipes.filter(recipe =>
            recipe.category.includes(category)
        );
    }
    
    renderRecipes(filteredRecipes);
}

/**
 * 渲染分类筛选按钮
 */
function renderCategoryFilters() {
    // 获取所有唯一的分类
    const categories = new Set();
    allRecipes.forEach(recipe => {
        recipe.category.forEach(cat => categories.add(cat));
    });
    
    const categoryContainer = document.getElementById('category-filters');
    if (!categoryContainer) return;
    
    // 先清空容器，防止重复添加
    categoryContainer.innerHTML = '';
    
    // 创建"全部"按钮
    const allBtn = document.createElement('button');
    allBtn.className = 'category-btn';
    allBtn.dataset.category = 'all';
    allBtn.textContent = '全部';
    allBtn.addEventListener('click', handleCategoryFilter);
    categoryContainer.appendChild(allBtn);
    
    // 根据当前选中的分类设置"全部"按钮的激活状态
    if (currentCategory === 'all') {
        allBtn.classList.add('active');
    }
    
    // 创建各分类按钮
    Array.from(categories).sort().forEach(category => {
        const btn = document.createElement('button');
        btn.className = 'category-btn';
        btn.dataset.category = category;
        btn.textContent = category;
        btn.addEventListener('click', handleCategoryFilter);
        
        // 根据当前选中的分类设置按钮的激活状态
        if (currentCategory === category) {
            btn.classList.add('active');
        }
        
        categoryContainer.appendChild(btn);
    });
}

/**
 * 渲染食谱卡片列表
 * @param {Array} recipes - 要渲染的食谱数组
 * @param {string} searchTerm - 搜索关键词（用于高亮）
 */
function renderRecipes(recipes, searchTerm = '') {
    const grid = document.getElementById('recipes-grid');
    if (!grid) return;
    
    // 清空现有内容
    grid.innerHTML = '';
    
    if (recipes.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <div class="empty-state-icon">🔍</div>
                <div class="empty-state-text">未找到匹配的食谱</div>
            </div>
        `;
        return;
    }
    
    // 渲染每个食谱卡片
    recipes.forEach(recipe => {
        const card = createRecipeCard(recipe, searchTerm);
        grid.appendChild(card);
    });
    
    // 初始化新添加图片的懒加载
    setTimeout(() => {
        initializeLazyLoading();
    }, 100);
}

/**
 * 创建单个食谱卡片
 * @param {Object} recipe - 食谱对象
 * @param {string} searchTerm - 搜索关键词（用于高亮）
 * @returns {HTMLElement} 卡片元素
 */
function createRecipeCard(recipe, searchTerm = '') {
    const card = document.createElement('div');
    card.className = 'recipe-card';
    card.setAttribute('data-recipe-id', recipe.id); // 添加 data-recipe-id 属性以便快速查找
    card.onclick = () => navigateToDetail(recipe.id);
    
    // 高亮搜索关键词
    const highlightText = (text) => {
        if (!searchTerm) return text;
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        return text.replace(regex, '<span class="highlight">$1</span>');
    };
    
    // 创建图片（支持懒加载和原始比例显示）
    const imageHtml = recipe.imageUrl ? `
        <div class="recipe-card-image loading">
            <img 
                data-src="${recipe.imageUrl}" 
                alt="${recipe.title}" 
                class="lazy-load"
                loading="lazy"
                onerror="this.classList.add('error'); this.parentElement.classList.remove('loading'); this.parentElement.innerHTML='<div style=\\'padding: 2rem; text-align: center; font-size: 3rem; color: var(--text-tertiary);\\'>🍽️</div>';"
            >
        </div>
    ` : `
        <div class="recipe-card-image">
            <div style="padding: 2rem; text-align: center; font-size: 3rem; color: var(--text-tertiary);">🍽️</div>
        </div>
    `;
    
    // 创建分类标签
    const categoryTags = recipe.category.map(cat => 
        `<span class="recipe-category-tag">${cat}</span>`
    ).join('');
    
    // 检查是否在购物清单中
    const inShoppingList = typeof isRecipeInShoppingList !== 'undefined' && isRecipeInShoppingList(recipe.id);
    
    // 创建卡片内容
    card.innerHTML = `
        ${imageHtml}
        <div class="recipe-card-content">
            <div class="recipe-card-header">
                <span class="recipe-card-id">#${recipe.id}</span>
                <h3 class="recipe-card-title">${highlightText(recipe.title)}</h3>
            </div>
            <p class="recipe-card-description">${highlightText(recipe.description || '')}</p>
            <div class="recipe-card-categories">
                ${categoryTags}
            </div>
            <div class="recipe-card-actions">
                <button class="add-to-shopping-list-btn ${inShoppingList ? 'added' : ''}" 
                        onclick="event.stopPropagation(); toggleRecipeInShoppingList(${recipe.id})"
                        title="${inShoppingList ? '已添加到购物清单' : '添加到购物清单'}"
                        data-recipe-id="${recipe.id}">
                    <span class="btn-icon">${inShoppingList ? '✓' : '🛒'}</span>
                    <span class="btn-text">${inShoppingList ? '已添加' : '加入清单'}</span>
                </button>
            </div>
        </div>
    `;
    
    return card;
}

/**
 * 导航到食谱详情页
 * @param {number} recipeId - 食谱ID
 */
function navigateToDetail(recipeId) {
    window.location.href = `recipe_detail.html?id=${recipeId}`;
}

/**
 * 加载并渲染食谱详情页
 */
function loadRecipeDetail() {
    // 从URL获取食谱ID
    const urlParams = new URLSearchParams(window.location.search);
    const recipeId = parseInt(urlParams.get('id'));
    
    if (!recipeId) {
        showError('未指定食谱ID');
        return;
    }
    
    // 等待数据加载完成
    if (allRecipes.length === 0) {
        // 如果数据还未加载，等待一下
        setTimeout(loadRecipeDetail, 100);
        return;
    }
    
    // 查找对应的食谱
    const recipe = allRecipes.find(r => r.id === recipeId);
    
    if (!recipe) {
        showError('未找到指定的食谱');
        return;
    }
    
    renderRecipeDetail(recipe);
    renderDetailSidebar(recipe); // 渲染详情页侧边栏
    
    // 初始化详情页图片的懒加载
    setTimeout(() => {
        initializeLazyLoading();
        adjustSidebarPosition(); // 调整侧边栏位置（详情页header可能更高）
    }, 100);
}

/**
 * 渲染食谱详情页
 * @param {Object} recipe - 食谱对象
 */
function renderRecipeDetail(recipe) {
    const detailContainer = document.getElementById('recipe-detail');
    if (!detailContainer) return;
    
    // 存储原始食材数据，用于分量调整
    window.currentRecipe = recipe;
    window.portionMultiplier = 1; // 默认1倍
    
    // 创建分类标签
    const categoryTags = recipe.category.map(cat => 
        `<span class="recipe-category-tag">${cat}</span>`
    ).join('');
    
    // 创建食材列表（带数据属性，用于动态更新）
    const ingredientsList = recipe.ingredients.map((ingredient, index) => `
        <li class="ingredient-item" data-index="${index}">
            <span class="ingredient-name">${ingredient.name}</span>
            <span class="ingredient-quantity" data-quantity="${ingredient.quantity}" data-unit="${ingredient.unit}">
                ${ingredient.quantity} ${ingredient.unit}
            </span>
        </li>
    `).join('');
    
    // 创建制作步骤列表（支持文本或对象格式）
    const instructionsList = recipe.instructions.map((instruction, index) => {
        let stepText = '';
        let stepImage = '';
        
        // 支持两种格式：字符串或对象
        if (typeof instruction === 'string') {
            stepText = instruction;
        } else if (typeof instruction === 'object' && instruction.text) {
            stepText = instruction.text;
            if (instruction.imageUrl) {
                stepImage = `
                    <div class="instruction-image">
                        <img src="${instruction.imageUrl}" 
                             alt="步骤 ${index + 1} 示意图" 
                             loading="lazy"
                             onerror="this.style.display='none'">
                    </div>
                `;
            }
        }
        
        return `
            <li class="instruction-item">
                ${stepImage}
                <div class="instruction-text">${stepText}</div>
            </li>
        `;
    }).join('');
    
    // 渲染详情页内容
    detailContainer.innerHTML = `
        <div class="recipe-detail-header">
            <h1 class="recipe-detail-title ${recipe.source ? 'clickable-title' : ''}" 
                ${recipe.source ? `onclick="window.open('${recipe.source}', '_blank', 'noopener,noreferrer')" title="点击查看来源"` : ''}>
                ${recipe.title}
                ${recipe.source ? '<span class="title-link-icon">🔗</span>' : ''}
            </h1>
            <div class="recipe-detail-categories">
                ${categoryTags}
            </div>
            ${recipe.description ? `<p class="recipe-detail-description">${recipe.description}</p>` : ''}
        </div>
        
        <div class="recipe-detail-image ${recipe.imageUrl ? 'loading' : ''}">
            ${recipe.imageUrl ? `
                <img 
                    data-src="${recipe.imageUrl}" 
                    alt="${recipe.title}" 
                    class="lazy-load"
                    loading="lazy"
                    onerror="this.classList.add('error'); this.parentElement.classList.remove('loading'); this.parentElement.innerHTML='<div style=\\'padding: 4rem; text-align: center; font-size: 4rem; color: var(--text-tertiary);\\'>🍽️</div>';"
                >
            ` : `
                <div style="padding: 4rem; text-align: center; font-size: 4rem; color: var(--text-tertiary);">🍽️</div>
            `}
        </div>
        
        <div class="recipe-section" id="ingredients">
            <div class="ingredients-header">
                <h2 class="recipe-section-title">食材清单</h2>
                <div class="portion-control">
                    <label for="portion-multiplier" class="portion-label">分量调整：</label>
                    <div class="portion-controls">
                        <button class="portion-btn" onclick="adjustPortion(-0.5)" title="减少0.5倍">-0.5</button>
                        <button class="portion-btn" onclick="adjustPortion(-0.25)" title="减少0.25倍">-0.25</button>
                        <input type="number" 
                               id="portion-multiplier" 
                               class="portion-input" 
                               value="1" 
                               min="0.25" 
                               max="10" 
                               step="0.25"
                               onchange="updatePortion(this.value)"
                               oninput="updatePortion(this.value)">
                        <span class="portion-display">倍</span>
                        <button class="portion-btn" onclick="adjustPortion(0.25)" title="增加0.25倍">+0.25</button>
                        <button class="portion-btn" onclick="adjustPortion(0.5)" title="增加0.5倍">+0.5</button>
                        <button class="portion-btn portion-reset" onclick="resetPortion()" title="重置为1倍">重置</button>
                    </div>
                </div>
            </div>
            <ul class="ingredients-list">
                ${ingredientsList}
            </ul>
        </div>
        
        ${recipe.nutrition ? `
        <div class="recipe-section" id="nutrition">
            <h2 class="recipe-section-title">营养信息</h2>
            <div class="nutrition-grid">
                <div class="nutrition-item" data-nutrition="calories">
                    <div class="nutrition-icon">🔥</div>
                    <div class="nutrition-content">
                        <div class="nutrition-label">热量</div>
                        <div class="nutrition-value" data-original="${recipe.nutrition.calories}">
                            ${recipe.nutrition.calories}
                        </div>
                        <div class="nutrition-unit">大卡</div>
                    </div>
                </div>
                <div class="nutrition-item" data-nutrition="protein">
                    <div class="nutrition-icon">💪</div>
                    <div class="nutrition-content">
                        <div class="nutrition-label">蛋白质</div>
                        <div class="nutrition-value" data-original="${recipe.nutrition.protein}">
                            ${recipe.nutrition.protein}
                        </div>
                        <div class="nutrition-unit">克</div>
                    </div>
                </div>
                <div class="nutrition-item" data-nutrition="carbs">
                    <div class="nutrition-icon">🌾</div>
                    <div class="nutrition-content">
                        <div class="nutrition-label">碳水化合物</div>
                        <div class="nutrition-value" data-original="${recipe.nutrition.carbs}">
                            ${recipe.nutrition.carbs}
                        </div>
                        <div class="nutrition-unit">克</div>
                    </div>
                </div>
                <div class="nutrition-item" data-nutrition="fat">
                    <div class="nutrition-icon">🥑</div>
                    <div class="nutrition-content">
                        <div class="nutrition-label">脂肪</div>
                        <div class="nutrition-value" data-original="${recipe.nutrition.fat}">
                            ${recipe.nutrition.fat}
                        </div>
                        <div class="nutrition-unit">克</div>
                    </div>
                </div>
                ${recipe.nutrition.salt !== undefined ? `
                <div class="nutrition-item" data-nutrition="salt">
                    <div class="nutrition-icon">🧂</div>
                    <div class="nutrition-content">
                        <div class="nutrition-label">盐（钠）</div>
                        <div class="nutrition-value" data-original="${recipe.nutrition.salt}">
                            ${recipe.nutrition.salt.toFixed(2)}
                        </div>
                        <div class="nutrition-unit">克</div>
                    </div>
                </div>
                ` : ''}
            </div>
        </div>
        ` : ''}
        
        <div class="recipe-section" id="instructions">
            <h2 class="recipe-section-title">制作方法</h2>
            <ol class="instructions-list">
                ${instructionsList}
            </ol>
        </div>
        
        ${recipe.source ? `
        <div class="recipe-section" id="source">
            <h2 class="recipe-section-title">来源</h2>
            <div class="recipe-source">
                <a href="${recipe.source}" target="_blank" rel="noopener noreferrer" class="source-link">
                    <span class="source-icon">🔗</span>
                    <span class="source-text">${recipe.source}</span>
                    <span class="source-external-icon">↗</span>
                </a>
            </div>
        </div>
        ` : ''}
        
        <div class="navigation-buttons">
            <a href="index.html" class="btn">返回主页</a>
            <button class="btn btn-secondary" onclick="window.print()">打印食谱</button>
        </div>
    `;
}

/**
 * 显示错误信息
 * @param {string} message - 错误消息
 */
function showError(message) {
    const container = document.getElementById('recipes-grid') || 
                     document.getElementById('recipe-detail');
    if (container) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <div class="empty-state-icon">⚠️</div>
                <div class="empty-state-text">${message}</div>
            </div>
        `;
    }
}

/**
 * 调整分量倍数
 * @param {number} delta - 调整的增量（可以是正数或负数）
 */
function adjustPortion(delta) {
    const input = document.getElementById('portion-multiplier');
    if (!input) return;
    
    const currentValue = parseFloat(input.value) || 1;
    const newValue = Math.max(0.25, Math.min(10, currentValue + delta));
    input.value = newValue.toFixed(2);
    updatePortion(newValue);
}

/**
 * 更新分量显示
 * @param {number|string} multiplier - 倍数
 */
function updatePortion(multiplier) {
    const multiplierValue = parseFloat(multiplier) || 1;
    
    // 限制范围
    const clampedMultiplier = Math.max(0.25, Math.min(10, multiplierValue));
    window.portionMultiplier = clampedMultiplier;
    
    // 更新输入框值
    const input = document.getElementById('portion-multiplier');
    if (input) {
        input.value = clampedMultiplier.toFixed(2);
    }
    
    // 更新所有食材分量
    const quantityElements = document.querySelectorAll('.ingredient-quantity');
    quantityElements.forEach(element => {
        const originalQuantity = parseFloat(element.getAttribute('data-quantity'));
        const unit = element.getAttribute('data-unit');
        const newQuantity = originalQuantity * clampedMultiplier;
        
        // 格式化显示：如果是整数则显示整数，否则保留1位小数
        let displayQuantity;
        if (newQuantity % 1 === 0) {
            displayQuantity = newQuantity.toString();
        } else if (newQuantity < 1) {
            // 小于1时保留2位小数
            displayQuantity = newQuantity.toFixed(2);
        } else {
            // 大于1时保留1位小数
            displayQuantity = newQuantity.toFixed(1);
        }
        
        element.textContent = `${displayQuantity} ${unit}`;
    });
    
    // 添加动画效果
    quantityElements.forEach(element => {
        element.classList.add('quantity-updated');
        setTimeout(() => {
            element.classList.remove('quantity-updated');
        }, 300);
    });
    
    // 更新营养信息（主内容区）
    const nutritionValues = document.querySelectorAll('.nutrition-value');
    nutritionValues.forEach(element => {
        const originalValue = parseFloat(element.getAttribute('data-original'));
        const newValue = originalValue * clampedMultiplier;
        
        // 格式化显示：盐含量保留2位小数，其他保留1位小数
        const nutritionType = element.closest('.nutrition-item')?.getAttribute('data-nutrition');
        const displayValue = nutritionType === 'salt' ? newValue.toFixed(2) : newValue.toFixed(1);
        element.textContent = displayValue;
        
        // 添加动画效果
        element.classList.add('nutrition-updated');
        setTimeout(() => {
            element.classList.remove('nutrition-updated');
        }, 300);
    });
    
    // 更新侧边栏营养信息摘要
    updateNutritionSummary(clampedMultiplier);
}

/**
 * 重置分量为1倍
 */
function resetPortion() {
    const input = document.getElementById('portion-multiplier');
    if (input) {
        input.value = '1';
        updatePortion(1);
    }
}

/**
 * 初始化懒加载功能
 */
function initializeLazyLoading() {
    // 使用 Intersection Observer API 实现懒加载
    if ('IntersectionObserver' in window) {
        // 如果已经存在observer，先断开
        if (window.imageObserver) {
            window.imageObserver.disconnect();
        }
        
        window.imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    const imageContainer = img.closest('.recipe-card-image, .recipe-detail-image');
                    
                    // 加载图片
                    if (img.dataset.src) {
                        // 设置加载状态
                        if (imageContainer) {
                            imageContainer.classList.add('loading');
                        }
                        
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        
                        // 图片加载完成
                        img.onload = function() {
                            img.classList.add('loaded');
                            if (imageContainer) {
                                imageContainer.classList.remove('loading');
                            }
                        };
                        
                        // 图片加载失败
                        img.onerror = function() {
                            img.classList.add('error');
                            if (imageContainer) {
                                imageContainer.classList.remove('loading');
                                // 显示占位符
                                if (imageContainer.classList.contains('recipe-card-image')) {
                                    imageContainer.innerHTML = '<div style="padding: 2rem; text-align: center; font-size: 3rem; color: var(--text-tertiary);">🍽️</div>';
                                } else {
                                    imageContainer.innerHTML = '<div style="padding: 4rem; text-align: center; font-size: 4rem; color: var(--text-tertiary);">🍽️</div>';
                                }
                            }
                        };
                    }
                    
                    observer.unobserve(img);
                }
            });
        }, {
            rootMargin: '50px' // 提前50px开始加载
        });
        
        // 观察所有懒加载图片
        document.querySelectorAll('img.lazy-load').forEach(img => {
            window.imageObserver.observe(img);
        });
    } else {
        // 降级方案：直接加载所有图片
        document.querySelectorAll('img.lazy-load').forEach(img => {
            if (img.dataset.src) {
                const imageContainer = img.closest('.recipe-card-image, .recipe-detail-image');
                if (imageContainer) {
                    imageContainer.classList.add('loading');
                }
                
                img.src = img.dataset.src;
                img.removeAttribute('data-src');
                
                img.onload = function() {
                    img.classList.add('loaded');
                    if (imageContainer) {
                        imageContainer.classList.remove('loading');
                    }
                };
            }
        });
    }
}

/**
 * 加载图片（用于动态添加的图片）
 */
function loadImage(img) {
    if (img.dataset.src) {
        const imageContainer = img.closest('.recipe-card-image, .recipe-detail-image');
        if (imageContainer) {
            imageContainer.classList.add('loading');
        }
        
        img.src = img.dataset.src;
        img.removeAttribute('data-src');
        
        img.onload = function() {
            img.classList.add('loaded');
            if (imageContainer) {
                imageContainer.classList.remove('loading');
            }
        };
        
        img.onerror = function() {
            img.classList.add('error');
            if (imageContainer) {
                imageContainer.classList.remove('loading');
                if (imageContainer.classList.contains('recipe-card-image')) {
                    imageContainer.innerHTML = '<div style="padding: 2rem; text-align: center; font-size: 3rem; color: var(--text-tertiary);">🍽️</div>';
                } else {
                    imageContainer.innerHTML = '<div style="padding: 4rem; text-align: center; font-size: 4rem; color: var(--text-tertiary);">🍽️</div>';
                }
            }
        };
    }
}

/**
 * 渲染主页侧边栏内容
 */
function renderSidebarContent() {
    // 渲染热门推荐
    renderPopularRecipes();
    
    // 渲染统计信息
    renderStatsInfo();
    
    // 渲染所有分类
    renderAllCategories();
}

/**
 * 渲染热门推荐
 */
function renderPopularRecipes() {
    const container = document.getElementById('popular-recipes');
    if (!container) return;
    
    // 按ID排序，显示前5个
    const popular = [...allRecipes]
        .sort((a, b) => a.id - b.id)
        .slice(0, 5);
    
    container.innerHTML = popular.map(recipe => `
        <a href="recipe_detail.html?id=${recipe.id}" class="popular-recipe-item">
            <span class="recipe-number">#${recipe.id}</span>
            <span class="recipe-title">${recipe.title}</span>
        </a>
    `).join('');
}

/**
 * 渲染统计信息
 */
function renderStatsInfo() {
    const container = document.getElementById('stats-info');
    if (!container) return;
    
    const totalRecipes = allRecipes.length;
    const categories = new Set();
    allRecipes.forEach(recipe => {
        recipe.category.forEach(cat => categories.add(cat));
    });
    
    container.innerHTML = `
        <div class="stat-item">
            <span class="stat-label">总食谱数</span>
            <span class="stat-value">${totalRecipes}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">分类数量</span>
            <span class="stat-value">${categories.size}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">有图片</span>
            <span class="stat-value">${allRecipes.filter(r => r.imageUrl).length}</span>
        </div>
    `;
}

/**
 * 渲染所有分类
 */
function renderAllCategories() {
    const container = document.getElementById('all-categories');
    if (!container) return;
    
    const categoryCounts = {};
    allRecipes.forEach(recipe => {
        recipe.category.forEach(cat => {
            categoryCounts[cat] = (categoryCounts[cat] || 0) + 1;
        });
    });
    
    const sortedCategories = Object.entries(categoryCounts)
        .sort((a, b) => b[1] - a[1]);
    
    container.innerHTML = sortedCategories.map(([cat, count]) => `
        <a href="#" class="category-link" onclick="filterByCategory('${cat}'); return false;">
            <span>${cat}</span>
            <span class="category-count">${count}</span>
        </a>
    `).join('');
}

/**
 * 渲染详情页侧边栏
 */
function renderDetailSidebar(recipe) {
    // 渲染目录导航
    renderDetailTOC(recipe);
    
    // 渲染相关食谱
    renderRelatedRecipes(recipe);
    
    // 渲染营养信息摘要
    renderNutritionSummary(recipe);
    
    // 渲染快速操作（包括来源链接）
    renderQuickActions(recipe);
}

/**
 * 渲染详情页目录导航
 */
function renderDetailTOC(recipe) {
    const container = document.getElementById('detail-toc');
    if (!container) return;
    
    const tocItems = [
        { id: 'recipe-image', label: '食谱图片', level: 1 },
        { id: 'ingredients', label: '食材清单', level: 1 },
        { id: 'nutrition', label: '营养信息', level: 1 },
        { id: 'instructions', label: '制作方法', level: 1 }
    ];
    
    container.innerHTML = tocItems.map(item => `
        <a href="#${item.id}" class="toc-item level-${item.level}" onclick="scrollToSection('${item.id}'); return false;">
            ${item.label}
        </a>
    `).join('');
}

/**
 * 渲染相关食谱
 */
function renderRelatedRecipes(recipe) {
    const container = document.getElementById('related-recipes');
    if (!container) return;
    
    // 找到相同分类的其他食谱
    const related = allRecipes
        .filter(r => r.id !== recipe.id && 
                r.category.some(cat => recipe.category.includes(cat)))
        .slice(0, 3);
    
    if (related.length === 0) {
        container.innerHTML = '<p style="color: var(--text-tertiary); font-size: var(--text-sm);">暂无相关食谱</p>';
        return;
    }
    
    container.innerHTML = related.map(r => `
        <a href="recipe_detail.html?id=${r.id}" class="related-recipe-item">
            ${r.imageUrl ? `<img src="${r.imageUrl}" alt="${r.title}" class="recipe-image" onerror="this.style.display='none';">` : ''}
            <div class="recipe-info">
                <div class="recipe-title">${r.title}</div>
                <div class="recipe-category">${r.category[0] || ''}</div>
            </div>
        </a>
    `).join('');
}

/**
 * 渲染营养信息摘要
 */
function renderNutritionSummary(recipe) {
    const container = document.getElementById('nutrition-summary');
    if (!container || !recipe.nutrition) return;
    
    const nutrition = recipe.nutrition;
    container.innerHTML = `
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🔥 热量</span>
            <span class="nutrition-summary-value" data-nutrition="calories" data-original="${nutrition.calories}">${nutrition.calories.toFixed(0)} 千卡</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🥩 蛋白质</span>
            <span class="nutrition-summary-value" data-nutrition="protein" data-original="${nutrition.protein}">${nutrition.protein.toFixed(1)} 克</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🍞 碳水</span>
            <span class="nutrition-summary-value" data-nutrition="carbs" data-original="${nutrition.carbs}">${nutrition.carbs.toFixed(1)} 克</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🧈 脂肪</span>
            <span class="nutrition-summary-value" data-nutrition="fat" data-original="${nutrition.fat}">${nutrition.fat.toFixed(1)} 克</span>
        </div>
        ${nutrition.salt !== undefined ? `
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🧂 盐</span>
            <span class="nutrition-summary-value" data-nutrition="salt" data-original="${nutrition.salt}">${nutrition.salt.toFixed(2)} 克</span>
        </div>
        ` : ''}
    `;
}

/**
 * 渲染快速操作（包括来源链接）
 * @param {Object} recipe - 食谱对象
 */
function renderQuickActions(recipe) {
    const container = document.querySelector('.quick-actions');
    if (!container) return;
    
    // 基础操作按钮
    let actionsHTML = `
        <button class="quick-action-btn" onclick="scrollToTop()">
            <span class="action-icon">⬆️</span>
            <span class="action-text">回到顶部</span>
        </button>
        <button class="quick-action-btn" onclick="window.print()">
            <span class="action-icon">🖨️</span>
            <span class="action-text">打印食谱</span>
        </button>
    `;
    
    // 如果有来源链接，添加来源链接按钮
    if (recipe.source) {
        actionsHTML += `
            <a href="${recipe.source}" 
               target="_blank" 
               rel="noopener noreferrer" 
               class="quick-action-btn quick-action-link">
                <span class="action-icon">🔗</span>
                <span class="action-text">查看来源</span>
                <span class="action-external-icon">↗</span>
            </a>
        `;
    }
    
    container.innerHTML = actionsHTML;
}

/**
 * 更新侧边栏营养信息摘要
 * @param {number} multiplier - 倍数
 */
function updateNutritionSummary(multiplier) {
    const summaryValues = document.querySelectorAll('#nutrition-summary .nutrition-summary-value');
    if (summaryValues.length === 0) return;
    
    summaryValues.forEach(element => {
        const originalValue = parseFloat(element.getAttribute('data-original'));
        const nutritionType = element.getAttribute('data-nutrition');
        const newValue = originalValue * multiplier;
        
        // 格式化显示
        let displayValue;
        let unit = '克';
        
        if (nutritionType === 'calories') {
            displayValue = newValue.toFixed(0);
            unit = '千卡';
        } else if (nutritionType === 'salt') {
            displayValue = newValue.toFixed(2);
        } else {
            displayValue = newValue.toFixed(1);
        }
        
        element.textContent = `${displayValue} ${unit}`;
        
        // 添加动画效果
        element.classList.add('nutrition-updated');
        setTimeout(() => {
            element.classList.remove('nutrition-updated');
        }, 300);
    });
}

/**
 * 滚动到指定区域
 */
function scrollToSection(sectionId) {
    const element = document.getElementById(sectionId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * 滚动到顶部
 */
function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    // 确保返回顶部时 header 展开
    setTimeout(function() {
        expandHeader();
    }, 100);
}

/**
 * 清除搜索和筛选
 */
function clearSearch() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = '';
    }
    currentCategory = 'all';
    filteredRecipes = allRecipes;
    renderRecipes(filteredRecipes);
    renderCategoryFilters();
}

/* ============================================
   移动端侧边栏控制功能
   ============================================ */

// 侧边栏状态管理
let mobileSidebarState = {
    left: false,
    right: false
};

// 触摸手势状态
let touchState = {
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    sidebar: null,
    isDragging: false
};

/**
 * 切换移动端侧边栏
 * @param {string} side - 'left' 或 'right'
 */
function toggleMobileSidebar(side) {
    const sidebar = document.getElementById(`sidebar-${side}`);
    const toggle = document.querySelector(`.mobile-sidebar-toggle-${side}`);
    const menuBarToggle = document.querySelector(`.sidebar-toggle-${side}`);
    const overlay = document.getElementById('sidebar-overlay');

    // 优先使用 menu bar 中的按钮（如果存在）
    const activeToggle = menuBarToggle || toggle;
    
    if (!sidebar || !activeToggle) return;

    const isOpen = mobileSidebarState[side];

    if (isOpen) {
        closeMobileSidebar(side);
    } else {
        // 先关闭其他侧边栏
        if (mobileSidebarState.left && side !== 'left') closeMobileSidebar('left');
        if (mobileSidebarState.right && side !== 'right') closeMobileSidebar('right');
        
        // 移动端打开侧边栏，桌面端在 menu bar 中也可以切换
        if (isMobileViewport()) {
            openMobileSidebar(side);
        } else {
            // 桌面端：如果侧边栏被隐藏，可以显示提示或直接显示
            // 这里保持原有逻辑，桌面端侧边栏应该始终可见
        }
    }
}

/**
 * 打开移动端侧边栏
 * @param {string} side - 'left' 或 'right'
 */
function openMobileSidebar(side) {
    const sidebar = document.getElementById(`sidebar-${side}`);
    const toggle = document.querySelector(`.mobile-sidebar-toggle-${side}`);
    const menuBarToggle = document.querySelector(`.sidebar-toggle-${side}`);
    const overlay = document.getElementById('sidebar-overlay');

    // 优先使用 menu bar 中的按钮（如果存在）
    const activeToggle = menuBarToggle || toggle;

    if (!sidebar || !activeToggle) return;

    // 只在移动端处理滚动位置和 body 类
    if (isMobileViewport()) {
        // 保存当前滚动位置（在设置 position: fixed 之前）
        const currentScrollTop = window.pageYOffset || document.documentElement.scrollTop;
        if (!window.savedScrollPosition && !document.body.classList.contains('sidebar-open')) {
            window.savedScrollPosition = currentScrollTop;
        }

        // 先设置 body 的 top 值，再添加 fixed 类，这样可以保持滚动位置
        if (!document.body.classList.contains('sidebar-open')) {
            document.body.style.top = `-${currentScrollTop}px`;
            document.body.classList.add('sidebar-open');
        }
    }

    sidebar.classList.add('mobile-open');
    activeToggle.setAttribute('aria-expanded', 'true');
    // 同时更新另一个按钮（如果存在）
    if (toggle && toggle !== activeToggle) toggle.setAttribute('aria-expanded', 'true');
    if (menuBarToggle && menuBarToggle !== activeToggle) menuBarToggle.setAttribute('aria-expanded', 'true');
    
    if (overlay) {
        overlay.classList.add('active');
        overlay.setAttribute('aria-hidden', 'false');
    }

    mobileSidebarState[side] = true;

    // 只在移动端初始化触摸手势
    if (isMobileViewport()) {
        initSidebarTouchGesture(sidebar, side);
    }

    // 更新 menu bar 按钮状态
    updateMenuBarButtons();
}

/**
 * 关闭移动端侧边栏
 * @param {string} side - 'left' 或 'right'
 */
function closeMobileSidebar(side) {
    const sidebar = document.getElementById(`sidebar-${side}`);
    const toggle = document.querySelector(`.mobile-sidebar-toggle-${side}`);
    const menuBarToggle = document.querySelector(`.sidebar-toggle-${side}`);
    const overlay = document.getElementById('sidebar-overlay');

    if (!sidebar) return;

    // 先更新状态
    mobileSidebarState[side] = false;

    // 移除侧边栏的展开状态
    sidebar.classList.remove('mobile-open');
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    if (menuBarToggle) menuBarToggle.setAttribute('aria-expanded', 'false');
    
    // 如果两个侧边栏都关闭了，移除遮罩层和 body 类
    if (!mobileSidebarState.left && !mobileSidebarState.right) {
        if (overlay) {
            overlay.classList.remove('active');
            overlay.setAttribute('aria-hidden', 'true');
        }
        // 只在移动端移除 sidebar-open 类
        if (isMobileViewport()) {
            // 恢复滚动位置的正确方法
            const savedScrollTop = window.savedScrollPosition || 0;
            document.body.classList.remove('sidebar-open');
            document.body.style.top = '';
            // 使用 requestAnimationFrame 确保 DOM 更新后再滚动
            requestAnimationFrame(function() {
                window.scrollTo(0, savedScrollTop);
                window.savedScrollPosition = undefined;
            });
        }
    }

    // 更新 menu bar 按钮状态
    updateMenuBarButtons();
}

/**
 * 关闭所有移动端侧边栏
 */
function closeAllMobileSidebars() {
    // 先更新状态，确保检查逻辑正确
    mobileSidebarState.left = false;
    mobileSidebarState.right = false;
    
    // 关闭所有侧边栏
    const leftSidebar = document.getElementById('sidebar-left');
    const rightSidebar = document.getElementById('sidebar-right');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (leftSidebar) {
        leftSidebar.classList.remove('mobile-open');
        const leftToggle = document.querySelector('.mobile-sidebar-toggle-left');
        const leftMenuBarToggle = document.querySelector('.sidebar-toggle-left');
        if (leftToggle) leftToggle.setAttribute('aria-expanded', 'false');
        if (leftMenuBarToggle) leftMenuBarToggle.setAttribute('aria-expanded', 'false');
    }
    
    if (rightSidebar) {
        rightSidebar.classList.remove('mobile-open');
        const rightToggle = document.querySelector('.mobile-sidebar-toggle-right');
        const rightMenuBarToggle = document.querySelector('.sidebar-toggle-right');
        if (rightToggle) rightToggle.setAttribute('aria-expanded', 'false');
        if (rightMenuBarToggle) rightMenuBarToggle.setAttribute('aria-expanded', 'false');
    }
    
    // 移除遮罩层和 body 类
    if (overlay) {
        overlay.classList.remove('active');
        overlay.setAttribute('aria-hidden', 'true');
    }
    
    // 只在移动端处理滚动位置
    if (isMobileViewport() && document.body.classList.contains('sidebar-open')) {
        const savedScrollTop = window.savedScrollPosition || 0;
        document.body.classList.remove('sidebar-open');
        document.body.style.top = '';
        // 使用 requestAnimationFrame 确保 DOM 更新后再滚动
        requestAnimationFrame(function() {
            window.scrollTo(0, savedScrollTop);
            window.savedScrollPosition = undefined;
        });
    }
}

/**
 * 检测是否为移动端视口
 * @returns {boolean}
 */
function isMobileViewport() {
    return window.innerWidth <= 768;
}

/**
 * 初始化侧边栏触摸手势
 * @param {HTMLElement} sidebar - 侧边栏元素
 * @param {string} side - 'left' 或 'right'
 */
function initSidebarTouchGesture(sidebar, side) {
    if (!sidebar) return;

    // 移除旧的事件监听器
    sidebar.removeEventListener('touchstart', handleSidebarTouchStart);
    sidebar.removeEventListener('touchmove', handleSidebarTouchMove);
    sidebar.removeEventListener('touchend', handleSidebarTouchEnd);

    // 添加新的事件监听器
    sidebar.addEventListener('touchstart', handleSidebarTouchStart, { passive: false });
    sidebar.addEventListener('touchmove', handleSidebarTouchMove, { passive: false });
    sidebar.addEventListener('touchend', handleSidebarTouchEnd, { passive: true });
}

/**
 * 处理侧边栏触摸开始
 */
function handleSidebarTouchStart(e) {
    if (!isMobileViewport()) return;

    const sidebar = e.currentTarget;
    const side = sidebar.id.includes('left') ? 'left' : 'right';
    
    touchState.startX = e.touches[0].clientX;
    touchState.startY = e.touches[0].clientY;
    touchState.currentX = touchState.startX;
    touchState.currentY = touchState.startY;
    touchState.sidebar = sidebar;
    touchState.isDragging = false;
}

/**
 * 处理侧边栏触摸移动
 */
function handleSidebarTouchMove(e) {
    if (!isMobileViewport() || !touchState.sidebar) return;

    touchState.currentX = e.touches[0].clientX;
    touchState.currentY = e.touches[0].clientY;

    const deltaX = touchState.currentX - touchState.startX;
    const deltaY = touchState.currentY - touchState.startY;

    // 判断是否为水平滑动
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
        touchState.isDragging = true;
        e.preventDefault();

        const sidebar = touchState.sidebar;
        const side = sidebar.id.includes('left') ? 'left' : 'right';
        
        // 只允许关闭方向的滑动
        if ((side === 'left' && deltaX < 0) || (side === 'right' && deltaX > 0)) {
            const translateX = side === 'left' ? deltaX : deltaX;
            sidebar.style.transform = `translateX(${translateX}px)`;
            sidebar.style.transition = 'none';
        }
    }
}

/**
 * 处理侧边栏触摸结束
 */
function handleSidebarTouchEnd(e) {
    if (!isMobileViewport() || !touchState.sidebar) return;

    const sidebar = touchState.sidebar;
    const side = sidebar.id.includes('left') ? 'left' : 'right';
    
    sidebar.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';

    if (touchState.isDragging) {
        const deltaX = touchState.currentX - touchState.startX;
        const threshold = 100; // 滑动阈值

        // 如果滑动距离超过阈值，关闭侧边栏
        if ((side === 'left' && deltaX < -threshold) || 
            (side === 'right' && deltaX > threshold)) {
            closeMobileSidebar(side);
        } else {
            // 否则恢复原状
            sidebar.style.transform = '';
        }
    }

    // 重置触摸状态
    touchState.sidebar = null;
    touchState.isDragging = false;
}

/**
 * 处理窗口大小变化
 */
function handleWindowResize() {
    // 如果从移动端切换到桌面端，关闭所有侧边栏
    if (!isMobileViewport()) {
        closeAllMobileSidebars();
    }
}

// 监听窗口大小变化
window.addEventListener('resize', handleWindowResize);

// 监听 ESC 键关闭侧边栏
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && isMobileViewport()) {
        closeAllMobileSidebars();
    }
});

// 页面加载完成后初始化（侧边栏相关）
document.addEventListener('DOMContentLoaded', function() {
    // 确保遮罩层存在
    if (!document.getElementById('sidebar-overlay')) {
        const overlay = document.createElement('div');
        overlay.id = 'sidebar-overlay';
        overlay.className = 'sidebar-overlay';
        overlay.setAttribute('aria-hidden', 'true');
        overlay.onclick = closeAllMobileSidebars;
        document.body.appendChild(overlay);
    }
    
    // 延迟初始化 Header 滚动功能，确保 DOM 完全加载
    setTimeout(function() {
        if (typeof initializeHeaderScroll === 'function') {
            initializeHeaderScroll();
        }
    }, 200);
});

/* ============================================
   Header 滚动收缩为 Menu Bar 功能
   ============================================ */

// Header 滚动状态管理
let headerScrollState = {
    lastScrollTop: 0,
    scrollThreshold: 100, // 滚动阈值（像素），超过此值才开始收缩
    topThreshold: 5, // 顶部阈值（像素），只有滚动到接近顶部时才展开
    isHeaderVisible: true,
    ticking: false, // 节流标志
    scrollDirection: null, // 滚动方向：'up' 或 'down'
    directionLock: false, // 方向锁定，避免在阈值附近反复切换
    lastStateChange: 0, // 上次状态改变的时间戳
    minStateChangeInterval: 150 // 最小状态改变间隔（毫秒），避免频繁切换
};

/**
 * 初始化 Header 滚动收缩功能
 */
function initializeHeaderScroll() {
    const header = document.getElementById('main-header');
    const menuBar = document.getElementById('menu-bar');
    
    if (!header || !menuBar) return;

    // 初始化 header 为展开状态
    header.classList.remove('header-compact');
    menuBar.classList.remove('menu-bar-visible');
    headerScrollState.isHeaderVisible = true;
    headerScrollState.lastScrollTop = window.pageYOffset || document.documentElement.scrollTop;
    headerScrollState.scrollDirection = null;
    headerScrollState.directionLock = false;
    headerScrollState.lastStateChange = 0;

    // 使用节流优化滚动事件处理
    window.addEventListener('scroll', handleHeaderScroll, { passive: true });
}

/**
 * 处理 Header 滚动事件（节流版本）
 */
function handleHeaderScroll() {
    if (headerScrollState.ticking) return;

    window.requestAnimationFrame(function() {
        processHeaderScroll();
        headerScrollState.ticking = false;
    });

    headerScrollState.ticking = true;
}

/**
 * 滚动结束检测（防抖）
 */
let scrollEndTimeout = null;
function handleScrollEnd() {
    clearTimeout(scrollEndTimeout);
    scrollEndTimeout = setTimeout(function() {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        // 滚动结束后，如果非常接近顶部，确保 header 展开
        if (scrollTop < headerScrollState.topThreshold) {
            expandHeader();
            // 重置方向锁定
            headerScrollState.directionLock = false;
            headerScrollState.scrollDirection = null;
        }
    }, 200);
}

/**
 * 处理 Header 滚动逻辑
 */
function processHeaderScroll() {
    const header = document.getElementById('main-header');
    const menuBar = document.getElementById('menu-bar');
    
    if (!header || !menuBar) return;

    // 如果侧边栏打开，不处理 header 收缩
    if (document.body.classList.contains('sidebar-open')) {
        return;
    }

    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
    const scrollDelta = scrollTop - headerScrollState.lastScrollTop;
    const currentTime = Date.now();

    // 防止状态频繁切换：检查最小间隔
    const timeSinceLastChange = currentTime - headerScrollState.lastStateChange;
    if (timeSinceLastChange < headerScrollState.minStateChangeInterval && headerScrollState.directionLock) {
        headerScrollState.lastScrollTop = scrollTop;
        handleScrollEnd();
        return;
    }

    // 在页面顶部附近时（非常接近顶部），确保 header 完全展开
    if (scrollTop < headerScrollState.topThreshold) {
        if (!headerScrollState.isHeaderVisible) {
            expandHeader();
            headerScrollState.directionLock = false;
            headerScrollState.scrollDirection = null;
        }
        headerScrollState.lastScrollTop = scrollTop;
        handleScrollEnd();
        return;
    }

    // 判断滚动方向（使用阈值，避免微小滚动导致切换）
    const scrollDeltaThreshold = 10;
    let currentDirection = null;

    if (Math.abs(scrollDelta) < scrollDeltaThreshold) {
        // 滚动距离太小，保持当前状态
        headerScrollState.lastScrollTop = scrollTop;
        handleScrollEnd();
        return;
    }

    if (scrollDelta > scrollDeltaThreshold) {
        currentDirection = 'down';
    } else if (scrollDelta < -scrollDeltaThreshold) {
        currentDirection = 'up';
    }

    // 如果方向改变，重置锁定
    if (headerScrollState.scrollDirection && headerScrollState.scrollDirection !== currentDirection) {
        headerScrollState.directionLock = false;
    }

    // 设置当前方向
    if (currentDirection) {
        headerScrollState.scrollDirection = currentDirection;
    }

    // 根据滚动方向和位置决定状态
    // 向下滚动且超过阈值：收缩 header 为 menu bar
    if (currentDirection === 'down' && scrollTop > headerScrollState.scrollThreshold) {
        if (headerScrollState.isHeaderVisible && !headerScrollState.directionLock) {
            compactHeader();
            headerScrollState.directionLock = true;
            headerScrollState.lastStateChange = currentTime;
        }
    }
    // 向上滚动：只有当滚动到接近顶部时才展开 header
    else if (currentDirection === 'up') {
        // 只有当滚动位置非常接近顶部时才展开
        if (scrollTop < headerScrollState.topThreshold) {
            if (!headerScrollState.isHeaderVisible && !headerScrollState.directionLock) {
                expandHeader();
                headerScrollState.directionLock = true;
                headerScrollState.lastStateChange = currentTime;
            }
        }
        // 如果向上滚动但还没到顶部，保持 menu bar 状态（不做任何操作）
    }

    // 更新最后滚动位置
    headerScrollState.lastScrollTop = scrollTop;

    // 检测滚动结束
    handleScrollEnd();
}

/**
 * 收缩 Header 为 Menu Bar
 */
function compactHeader() {
    const header = document.getElementById('main-header');
    const menuBar = document.getElementById('menu-bar');
    
    if (!header || !menuBar) return;

    // 如果已经是收缩状态，不重复操作
    if (!headerScrollState.isHeaderVisible) return;

    header.classList.add('header-compact');
    menuBar.classList.add('menu-bar-visible');
    headerScrollState.isHeaderVisible = false;
    headerScrollState.lastStateChange = Date.now();

    // 更新 menu bar 中的按钮状态
    updateMenuBarButtons();
}

/**
 * 展开 Header
 */
function expandHeader() {
    const header = document.getElementById('main-header');
    const menuBar = document.getElementById('menu-bar');
    
    if (!header || !menuBar) return;

    // 如果已经是展开状态，不重复操作
    if (headerScrollState.isHeaderVisible) return;

    header.classList.remove('header-compact');
    menuBar.classList.remove('menu-bar-visible');
    headerScrollState.isHeaderVisible = true;
    headerScrollState.lastStateChange = Date.now();
    headerScrollState.directionLock = false; // 展开时重置锁定

    // 更新 menu bar 中的按钮状态
    updateMenuBarButtons();
}

/**
 * 更新 Menu Bar 中的按钮状态
 */
function updateMenuBarButtons() {
    // 更新 menu bar 中侧边栏按钮的 aria-expanded 状态
    const leftToggle = document.querySelector('.sidebar-toggle-left');
    const rightToggle = document.querySelector('.sidebar-toggle-right');
    
    if (leftToggle) {
        const leftSidebar = document.getElementById('sidebar-left');
        const isOpen = leftSidebar && leftSidebar.classList.contains('mobile-open');
        leftToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }
    
    if (rightToggle) {
        const rightSidebar = document.getElementById('sidebar-right');
        const isOpen = rightSidebar && rightSidebar.classList.contains('mobile-open');
        rightToggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    }
}
