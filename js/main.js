/**
 * 食谱管理系统 - 主JavaScript文件
 * 负责数据加载、搜索、筛选和页面渲染
 */

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
});

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
            <h1 class="recipe-detail-title">${recipe.title}</h1>
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
    
    // 更新营养信息
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
            <span class="nutrition-summary-value">${nutrition.calories.toFixed(0)} 千卡</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🥩 蛋白质</span>
            <span class="nutrition-summary-value">${nutrition.protein.toFixed(1)} 克</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🍞 碳水</span>
            <span class="nutrition-summary-value">${nutrition.carbs.toFixed(1)} 克</span>
        </div>
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🧈 脂肪</span>
            <span class="nutrition-summary-value">${nutrition.fat.toFixed(1)} 克</span>
        </div>
        ${nutrition.salt !== undefined ? `
        <div class="nutrition-summary-item">
            <span class="nutrition-summary-label">🧂 盐</span>
            <span class="nutrition-summary-value">${nutrition.salt.toFixed(2)} 克</span>
        </div>
        ` : ''}
    `;
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
