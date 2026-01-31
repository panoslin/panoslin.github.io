---
name: add-recipe
description: Add a new recipe to the recipe database by extracting information from images, updating recipes.json, managing recipe images, and calculating nutritional information.
---

# Add Recipe Skill

This skill handles the complete workflow for adding a new recipe to the recipe database, including image processing, JSON updates, nutrition calculation, and ingredient database maintenance.

## When to Use

- Use this skill when the user provides recipe images (screenshots or photos)、text description and wants to add a new recipe to `recipes.json`
- Use this skill when the user says "添加这道食谱" or "add this recipe" with attached images and/or text description
- This skill is helpful for systematically processing recipe information from visual sources

## Instructions

### Step 1: Read Recipe Images

1. **Identify recipe images**: Look for attached image files (screenshots, photos) that contain recipe information
2. **Extract recipe details** from images:
   - **Title**: The dish name (usually at the top or in the first image)
   - **Ingredients**: List all ingredients with quantities and units (e.g., "去骨鸡腿肉 400克", "杏鲍菇 300克")
   - **Instructions**: Extract cooking steps in order (usually numbered or sequential)
   - **Category**: Determine appropriate categories (e.g., "中餐", "家常菜", "海鲜", "凉菜")
   - **Description**: Create a brief description summarizing the dish

3. **Parse ingredient format**: 
   - Each ingredient should have: `name`, `quantity` (number), `unit` (e.g., "克", "毫升", "个")
   - Normalize units: "克" = "g", "毫升" = "ml", "个" = "个"
   - Handle special cases like "瓣" (clove), "头" (head of garlic), "滴" (drop)

### Step 2: Write to recipes.json

1. **Determine next recipe ID**:
   - Read `recipes.json` and find the highest `id` value
   - New recipe ID = highest ID + 1

2. **Create recipe entry** with the following structure:
   ```json
   {
     "id": <next_id>,
     "title": "<dish name>",
     "category": ["<category1>", "<category2>"],
     "imageUrl": "images/recipe_<id>.png",
     "description": "<brief description>",
     "ingredients": [
       {
         "name": "<ingredient name>",
         "quantity": <number>,
         "unit": "<unit>"
       }
     ],
     "instructions": [
       "<step 1>",
       "<step 2>",
       ...
     ],
     "nutrition": {
       "calories": 0,
       "protein": 0,
       "carbs": 0,
       "fat": 0,
       "salt": 0
     },
     "source": "<optional source URL>"
   }
   ```

3. **Append to recipes.json**:
   - Read the entire JSON array
   - Add the new recipe object
   - Write back with proper formatting (`ensure_ascii=False, indent=2`)

### Step 3: Handle Recipe Images

1. **Select cover image**:
   - Choose the first image or the most representative image as the cover
   - If multiple images are provided, prefer the one showing the final dish

2. **Move/rename cover image**:
   - Target filename: `images/recipe_<id>.png` (where `<id>` is the new recipe ID)
   - If the image is already in the workspace, copy or move it to the `images/` directory
   - If the image needs to be downloaded from a URL, use appropriate tools

3. **Handle step images** (automatic detection and processing):
   
   **Identify steps that require images**:
   - Steps that describe visual techniques (e.g., "切花刀", "改刀", "摆盘", "装饰")
   - Steps involving specific shapes, cuts, or arrangements (e.g., "切成菱形", "摆成圆形", "交叉一字花刀")
   - Steps showing intermediate states that are hard to describe (e.g., "炒至焦糖色", "炸至金黄", "煮至冒泡")
   - Steps with complex procedures that benefit from visual demonstration
   - Steps mentioning specific visual cues (e.g., "看到...", "呈现...", "出现...")
   
   **Match images to steps**:
   - Analyze all provided images (excluding the cover image)
   - For each step that requires visual demonstration:
     - Look for images that show the described action or result
     - Match images to steps based on:
       - Visual content (what the image shows)
       - Sequential order (if images are in order)
       - Text cues in the image (if any)
   - If multiple images are provided and their order is clear, match them sequentially to steps
   
   **Process step images automatically**:
   - For each matched step image:
     1. Determine the step number (1-indexed)
     2. Move/rename the image to: `images/recipe_<id>_step_<step_number>.png`
     3. Update the corresponding instruction entry in `instructions` array:
        - If the instruction is a string, convert it to an object:
          ```json
          {
            "text": "<original step description>",
            "imageUrl": "images/recipe_<id>_step_<step_number>.png"
          }
          ```
        - If it's already an object, add the `imageUrl` field
   
   **Example transformation**:
   - Before:
     ```json
     "instructions": [
       "首先把鲈鱼处理干净，开背，改成交叉一字花刀，方便入味和蒸制。",
       "准备适量葱姜丝，用手抓揉出葱姜汁。"
     ]
     ```
   - After (if step 1 has a matching image):
     ```json
     "instructions": [
       {
         "text": "首先把鲈鱼处理干净，开背，改成交叉一字花刀，方便入味和蒸制。",
         "imageUrl": "images/recipe_41_step_1.png"
       },
       "准备适量葱姜丝，用手抓揉出葱姜汁。"
     ]
     ```
   
   **Best practices for step images**:
   - Only add images to steps that truly benefit from visual demonstration
   - Don't add images to simple text-only steps (e.g., "加盐调味")
   - If unsure whether a step needs an image, err on the side of including it if a relevant image exists
   - Maintain consistency: if one step has an image, consider if adjacent steps also need images

### Step 4: Calculate and Update Nutrition

1. **Run nutrition calculation**:
   - Use `calculate_nutrition.py` to compute nutrition for the new recipe
   - Execute: `python3 -c "import json; import calculate_nutrition as cn; ..."`
   - Update the recipe's `nutrition` field in `recipes.json`

2. **Handle missing ingredients**:
   - If `calculate_nutrition.py` reports missing ingredients (warns about ingredients not in `NUTRITION_DB`):
     - Identify all missing ingredient names
     - Search for authoritative nutrition data (use web search if needed)
     - Add missing ingredients to `NUTRITION_DB` in `calculate_nutrition.py` with format:
       ```python
       '<ingredient name>': {
           'calories': <kcal per 100g>,
           'protein': <g per 100g>,
           'carbs': <g per 100g>,
           'fat': <g per 100g>,
           'salt': <mg sodium per 100g>,
           'unit': 'g' or 'ml'
       }
       ```
   - **Nutrition data sources**: Use Chinese Food Composition Table, USDA database, or other authoritative sources
   - **Important**: 
     - `salt` field stores **sodium in milligrams per 100g**, not salt content
     - For liquid ingredients (like 黄酒), use `'unit': 'ml'`
     - For solid ingredients, use `'unit': 'g'`

3. **Recalculate after adding ingredients**:
   - After adding missing ingredients to `NUTRITION_DB`, recalculate nutrition
   - Update the recipe's `nutrition` field again

### Step 5: Verification

1. **Verify recipe entry**:
   - Check that all required fields are present
   - Ensure `imageUrl` points to an existing file
   - Verify ingredient quantities and units are correct

2. **Verify nutrition calculation**:
   - Confirm nutrition values are reasonable (not all zeros)
   - Check that no warnings about missing ingredients remain

## Best Practices

- **Ingredient normalization**: 
  - Use consistent naming (e.g., always use "去骨鸡腿肉" not "鸡腿肉去骨")
  - Normalize units: prefer "克" over "g" for consistency with existing recipes
  - Handle variations: "耗油" = "蚝油", "蒜末" = "蒜蓉" = "蒜"

- **Category selection**:
  - Use existing categories when possible
  - Common categories: "中餐", "西餐", "家常菜", "海鲜", "凉菜", "汤品", "饮品", "甜点", "低脂", "粤菜"

- **Image handling**:
  - Always use PNG format for recipe images
  - Ensure images are properly named and placed in `images/` directory
  - If user provides multiple images, ask which one should be the cover if unclear
  
- **Step images optimization**:
  - Automatically detect steps that require visual demonstration
  - Match images to steps intelligently based on content and order
  - Only add images to steps that truly benefit from visual aid
  - Convert string instructions to objects with `text` and `imageUrl` fields when adding step images
  - Maintain backward compatibility: steps without images remain as strings

- **Nutrition accuracy**:
  - Always add missing ingredients to `calculate_nutrition.py` for future use
  - Use authoritative nutrition databases for ingredient data
  - Document the source of nutrition data in comments if needed

- **Error handling**:
  - If recipe images are unclear, ask the user for clarification
  - If ingredient quantities are ambiguous, make reasonable estimates and note them
  - If nutrition calculation fails, investigate the cause (missing ingredients, unit mismatches, etc.)

## Example Workflow

1. User provides 10 screenshots of a recipe video
2. Extract: title "杏鲍菇鸡腿一锅焖", ingredients list, 8 cooking steps
3. Determine next ID: 35
4. Create recipe entry with `imageUrl: "images/recipe_35.png"`
5. Select first screenshot as cover, save as `images/recipe_35.png`
6. **Analyze remaining 9 images for step matching**:
   - Identify steps requiring visual aid (e.g., step 1: "杏鲍菇用刮皮刀刨成薄片")
   - Match images to steps based on content and order
   - Automatically move/rename: `images/recipe_35_step_1.png`, `recipe_35_step_3.png`, etc.
   - Update `instructions` array: convert matching steps to objects with `imageUrl`
7. Calculate nutrition → warnings about "去骨鸡腿肉", "杏鲍菇", "黄酒", "黑胡椒"
8. Add these ingredients to `calculate_nutrition.py` with accurate nutrition data
9. Recalculate nutrition → update recipe
10. Verify all fields are complete, including step images

## Notes

- The `salt` field in nutrition represents **salt content in grams**, calculated from sodium content
- Conversion: salt (g) = sodium (mg) / 1000 * 2.54
- Some ingredients may have special units (个, 头, 瓣, 滴) that require special handling in `calculate_nutrition.py`
- Always preserve existing recipes when updating `recipes.json` - never overwrite or delete existing entries
