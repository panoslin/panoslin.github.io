/**
 * Nutrition utilities (shared)
 * - Browser: attaches to window.NutritionUtils
 * - Node: module.exports
 */

(function (root, factory) {
    if (typeof module === 'object' && typeof module.exports === 'object') {
        module.exports = factory();
    } else {
        root.NutritionUtils = factory();
    }
}(typeof window !== 'undefined' ? window : globalThis, function () {
    function normalizeScale(scale) {
        const n = Number(scale);
        if (!Number.isFinite(n) || n <= 0) return 1;
        return Math.min(Math.max(n, 0.1), 20);
    }

    function emptyTotals() {
        return { calories: 0, protein: 0, carbs: 0, fat: 0, salt: 0 };
    }

    /**
     * Sum nutrition across selected recipes (respecting recipeScales)
     * @param {Object} shoppingData - output of loadShoppingList()
     * @param {Array} allRecipes - recipes.json array
     * @returns {{calories:number,protein:number,carbs:number,fat:number,salt:number}}
     */
    function sumNutritionForShoppingList(shoppingData, allRecipes) {
        if (!shoppingData || !Array.isArray(allRecipes)) return emptyTotals();
        const ids = Array.isArray(shoppingData.selectedRecipeIds) ? shoppingData.selectedRecipeIds : [];
        const scales = (shoppingData.recipeScales && typeof shoppingData.recipeScales === 'object') ? shoppingData.recipeScales : {};

        const totals = emptyTotals();

        ids.forEach((id) => {
            const recipe = allRecipes.find(r => r && r.id === id);
            if (!recipe || !recipe.nutrition) return;
            const scale = normalizeScale(scales[id] !== undefined ? scales[id] : 1);
            const n = recipe.nutrition;

            totals.calories += (Number(n.calories) || 0) * scale;
            totals.protein += (Number(n.protein) || 0) * scale;
            totals.carbs += (Number(n.carbs) || 0) * scale;
            totals.fat += (Number(n.fat) || 0) * scale;
            totals.salt += (Number(n.salt) || 0) * scale;
        });

        return totals;
    }

    return {
        normalizeScale,
        sumNutritionForShoppingList,
        emptyTotals
    };
}));

