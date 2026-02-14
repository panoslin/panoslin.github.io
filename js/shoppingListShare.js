/**
 * 购物清单分享功能模块
 * 支持将购物清单编码到 URL 并分享
 */

/**
 * 将购物清单数据编码为 URL 参数
 * @param {Object} shoppingListData - 购物清单数据 { ingredients, selectedRecipeIds, recipeScales }
 * @returns {string} 编码后的 URL 参数
 */
function encodeShoppingListToUrl(shoppingListData) {
    if (!shoppingListData || !shoppingListData.selectedRecipeIds || shoppingListData.selectedRecipeIds.length === 0) {
        return null;
    }
    
    // 只编码必要的数据：选中的食谱ID和对应的分量比例
    const payload = {
        recipes: shoppingListData.selectedRecipeIds,
        scales: shoppingListData.recipeScales || {}
    };
    
    try {
        // 将数据转换为 JSON 字符串
        const jsonString = JSON.stringify(payload);
        // 使用 base64 编码（URL 安全）
        // 先转换为 UTF-8 字节，再 base64 编码
        const utf8Bytes = new TextEncoder().encode(jsonString);
        const base64String = btoa(String.fromCharCode(...utf8Bytes));
        // URL 编码以确保安全
        return encodeURIComponent(base64String);
    } catch (e) {
        console.error('编码购物清单失败:', e);
        return null;
    }
}

/**
 * 从 URL 参数解码购物清单数据
 * @param {string} encoded - 编码后的字符串
 * @returns {Object|null} 解码后的购物清单数据 { recipes, scales }
 */
function decodeShoppingListFromUrl(encoded) {
    if (!encoded || typeof encoded !== 'string') {
        return null;
    }
    
    try {
        // URL 解码
        const base64String = decodeURIComponent(encoded);
        // 解码 base64
        const binaryString = atob(base64String);
        // 转换为 UTF-8 字节
        const utf8Bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            utf8Bytes[i] = binaryString.charCodeAt(i);
        }
        // 解码为字符串
        const decoded = new TextDecoder().decode(utf8Bytes);
        // 解析 JSON
        const payload = JSON.parse(decoded);
        
        // 验证数据结构
        if (!payload.recipes || !Array.isArray(payload.recipes)) {
            return null;
        }
        
        return {
            recipes: payload.recipes,
            scales: payload.scales || {}
        };
    } catch (e) {
        console.error('解码购物清单失败:', e);
        return null;
    }
}

/**
 * 生成分享链接
 * @param {Object} shoppingListData - 购物清单数据
 * @returns {string|null} 分享链接，如果数据无效则返回 null
 */
function generateShareLink(shoppingListData) {
    const encoded = encodeShoppingListToUrl(shoppingListData);
    if (!encoded) {
        return null;
    }
    
    // 获取当前页面的基础 URL
    const baseUrl = window.location.origin + window.location.pathname.replace(/[^/]*$/, '');
    // 生成分享链接，跳转到购物清单页面
    const shareUrl = `${baseUrl}shopping_list.html?share=${encoded}`;
    return shareUrl;
}

/**
 * 复制文本到剪贴板
 * @param {string} text - 要复制的文本
 * @returns {Promise<boolean>} 是否复制成功
 */
async function copyToClipboard(text) {
    try {
        // 优先使用现代 Clipboard API
        if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        }
        
        // 降级方案：使用传统方法
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
            document.body.removeChild(textArea);
            return successful;
        } catch (e) {
            document.body.removeChild(textArea);
            return false;
        }
    } catch (e) {
        console.error('复制到剪贴板失败:', e);
        return false;
    }
}

/**
 * 分享购物清单
 * @returns {Promise<boolean>} 是否分享成功
 */
async function shareShoppingList() {
    // 确保购物清单模块已加载
    if (typeof loadShoppingList === 'undefined') {
        console.error('购物清单模块未加载');
        return false;
    }
    
    const shoppingListData = loadShoppingList();
    
    // 检查是否有选中的食谱
    if (!shoppingListData.selectedRecipeIds || shoppingListData.selectedRecipeIds.length === 0) {
        alert('购物清单是空的，无法分享。请先添加一些食谱到购物清单。');
        return false;
    }
    
    const shareUrl = generateShareLink(shoppingListData);
    if (!shareUrl) {
        alert('生成分享链接失败，请稍后重试。');
        return false;
    }
    
    // 复制到剪贴板
    const success = await copyToClipboard(shareUrl);
    if (success) {
        // 显示成功提示
        showShareSuccessMessage();
        return true;
    } else {
        alert('复制链接失败，请手动复制：\n' + shareUrl);
        return false;
    }
}

/**
 * 显示分享成功提示
 */
function showShareSuccessMessage() {
    // 创建提示元素
    const toast = document.createElement('div');
    toast.className = 'share-toast';
    toast.textContent = '✅ 分享链接已复制到剪贴板！';
    
    // 添加到页面
    document.body.appendChild(toast);
    
    // 显示动画
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // 3秒后移除
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
 * 从 URL 参数加载分享的购物清单
 * @returns {boolean} 是否成功加载
 */
function loadSharedShoppingList() {
    // 获取 URL 参数
    const urlParams = new URLSearchParams(window.location.search);
    const shareParam = urlParams.get('share');
    
    if (!shareParam) {
        return false;
    }
    
    // 解码数据
    const decoded = decodeShoppingListFromUrl(shareParam);
    if (!decoded || !decoded.recipes || decoded.recipes.length === 0) {
        console.error('无效的分享链接');
        return false;
    }
    
    // 确保食谱数据已加载
    if (typeof allRecipes === 'undefined' || !allRecipes || allRecipes.length === 0) {
        console.warn('食谱数据未加载，等待加载...');
        setTimeout(loadSharedShoppingList, 100);
        return false;
    }
    
    // 确保购物清单模块已加载
    if (typeof collectIngredientsFromRecipes === 'undefined' || typeof saveShoppingList === 'undefined') {
        console.warn('购物清单模块未加载，等待加载...');
        setTimeout(loadSharedShoppingList, 100);
        return false;
    }
    
    // 验证食谱ID是否有效
    const validRecipeIds = decoded.recipes.filter(id => {
        return allRecipes.some(r => r.id === id);
    });
    
    if (validRecipeIds.length === 0) {
        alert('分享链接中的食谱不存在或已删除。');
        return false;
    }
    
    // 规范化分量比例
    const normalizedScales = {};
    validRecipeIds.forEach(id => {
        let scale = decoded.scales && decoded.scales[id] !== undefined 
            ? decoded.scales[id] 
            : 1;
        // 使用 normalizeScale 如果可用，否则手动规范化
        if (typeof normalizeScale === 'function') {
            scale = normalizeScale(scale);
        } else {
            const n = Number(scale);
            scale = (!Number.isFinite(n) || n <= 0) ? 1 : Math.min(Math.max(n, 0.1), 20);
        }
        normalizedScales[id] = scale;
    });
    
    // 收集食材
    const ingredients = collectIngredientsFromRecipes(validRecipeIds, allRecipes, normalizedScales);
    
    // 保存到 localStorage
    saveShoppingList(ingredients, validRecipeIds, normalizedScales);
    
    // 清除 URL 参数，避免重复加载
    const newUrl = window.location.pathname;
    window.history.replaceState({}, '', newUrl);
    
    // 显示成功提示
    showSharedListLoadedMessage(validRecipeIds.length);
    
    return true;
}

/**
 * 显示分享清单加载成功提示
 * @param {number} recipeCount - 加载的食谱数量
 */
function showSharedListLoadedMessage(recipeCount) {
    const toast = document.createElement('div');
    toast.className = 'share-toast share-toast-success';
    toast.textContent = `✅ 已加载 ${recipeCount} 个食谱到购物清单！`;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}
