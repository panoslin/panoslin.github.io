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
   
   **CRITICAL: Text expansion and enhancement**:
   - **DO NOT simply copy text from images verbatim**
   - **Understand and expand**: Read the text on images, understand its meaning, then write it in a clear, complete, and easy-to-understand way
   - **Fill in implicit information**: If the image text is brief or abbreviated, expand it with necessary details
   - **Clarify ambiguous terms**: If abbreviations or unclear terms appear, write them out fully
   - **Improve readability**: Make the text flow naturally and be self-explanatory
   - **Maintain accuracy**: While expanding, ensure the meaning remains accurate and faithful to the original
   
   **Examples of text expansion**:
   - Image text: "鲈鱼 1条" → Expanded: "新鲜鲈鱼 1条（约500克）"
   - Image text: "葱姜丝" → Expanded: "适量葱姜丝"
   - Image text: "改刀" → Expanded: "改成交叉一字花刀"
   - Image text: "蒸10分钟" → Expanded: "大火蒸制10分钟"
   - Image text: "调味" → Expanded: "加盐、生抽调味"
   - Image text: "摆盘" → Expanded: "将菜品摆盘装饰"
   
   **Extract and enhance recipe details**:
   - **Title**: The dish name (usually at the top or in the first image)
     - If abbreviated, expand to full name
     - Ensure it's clear and descriptive
   - **Ingredients**: List all ingredients with quantities and units
     - Expand abbreviated ingredient names (e.g., "鸡腿肉" → "去骨鸡腿肉")
     - Add reasonable quantities if only names are given (e.g., "适量" → "适量" or estimate based on context)
     - Clarify preparation state if mentioned (e.g., "洗净", "切段")
   - **Instructions**: Extract cooking steps in order (usually numbered or sequential)
     - **Expand brief instructions**: If step is too brief, add necessary details
       - Example: "改刀" → "将鲈鱼改成交叉一字花刀，方便入味和蒸制"
       - Example: "腌制" → "加盐、料酒腌制10分钟"
     - **Clarify cooking methods**: Specify heat level, time, and technique when mentioned
       - Example: "炒" → "大火快速翻炒"
       - Example: "煮" → "大火烧开后转小火煮制"
     - **Complete incomplete sentences**: If instruction is fragmentary, make it a complete sentence
     - **Maintain logical flow**: Ensure each step flows naturally to the next
   - **Category**: Determine appropriate categories (e.g., "中餐", "家常菜", "海鲜", "凉菜")
   - **Description**: Create a brief description summarizing the dish
     - Don't just copy from image - write a clear, engaging description
     - Include key characteristics: cooking method, flavor profile, difficulty level

3. **Parse ingredient format** (with expansion): 
   - Each ingredient should have: `name`, `quantity` (number), `unit` (e.g., "克", "毫升", "个")
   - **Expand ingredient names**: Don't just copy abbreviated names from images
     - "鸡腿肉" → "去骨鸡腿肉" (if bone is removed)
     - "葱姜" → "葱姜丝" or "葱段、姜片" (specify preparation)
     - "蒜" → "大蒜" or "蒜瓣" (clarify form)
   - **Add missing quantities**: If image only shows name, estimate reasonable quantity based on context
   - **Clarify preparation state**: If mentioned in image, include it (e.g., "洗净", "切段", "去皮")
   - Normalize units: "克" = "g", "毫升" = "ml", "个" = "个"
   - Handle special cases like "瓣" (clove), "头" (head of garlic), "滴" (drop)
   - **Examples of expansion**:
     - Image: "鸡腿 1个" → Expanded: "去骨鸡腿肉 400克"
     - Image: "杏鲍菇" → Expanded: "杏鲍菇 300克"
     - Image: "黄酒" → Expanded: "黄酒 30毫升"
     - Image: "盐 适量" → Expanded: "盐 适量" (keep if appropriate)

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

3. **Handle step images** (selective and necessary only):
   
   **CRITICAL PRINCIPLE**: Not every step needs an image. Only add images when they provide essential visual information that cannot be adequately conveyed through text alone. **Quality over quantity** - it's better to have fewer, meaningful step images than to add images to every step.
   
   **IMPORTANT: Screenshot filename order**:
   - Screenshot filenames often contain **sequential order information** that represents the order of steps in the recipe video
   - This order information can be:
     - **Timestamps**: e.g., `Screenshot 2026-01-30 at 00.09.02.png`, `Screenshot 2026-01-30 at 00.09.22.png` (later timestamp = later step)
     - **Sequential numbers**: e.g., `IMG_7977.PNG`, `IMG_7978.PNG`, `IMG_7979.PNG` (higher number = later step)
     - **Other sequential patterns**: Any pattern that indicates order (e.g., `photo_1.png`, `photo_2.png`)
   - **Extract and use this order information**:
     1. When analyzing screenshots, first extract the order from filenames
     2. Sort screenshots by their order (chronological or numerical)
     3. Use this order as a **primary indicator** for matching images to steps
     4. The first screenshot (by order) likely corresponds to step 1, second to step 2, etc.
   - **Order is a strong signal**: If filenames indicate clear sequential order, prioritize this over other matching strategies
   
   **Steps that DO require images** (only if they meet these criteria):
   - **Visual techniques that are hard to describe**: Steps describing specific cutting techniques, arrangements, or visual patterns (e.g., "切花刀", "改成交叉一字花刀", "摆成圆形", "装饰")
   - **Specific visual outcomes**: Steps where the visual result is critical to success (e.g., "炒至焦糖色", "炸至金黄", "煮至冒泡", "呈现...")
   - **Complex spatial arrangements**: Steps involving specific positioning, layering, or arrangement (e.g., "铺一层...再铺一层...", "摆盘", "交叉摆放")
   - **Visual identification needed**: Steps where visual cues are essential (e.g., "看到...", "呈现...", "出现...")
   - **Unusual or non-standard techniques**: Steps that demonstrate techniques not commonly known
   
   **Steps that DO NOT require images** (most common cases):
   - **Simple text-only steps**: Basic actions that are clearly described (e.g., "加盐调味", "搅拌均匀", "腌制10分钟")
   - **Standard cooking operations**: Common procedures that don't need visual aid (e.g., "倒入锅中", "大火烧开", "转小火")
   - **Simple ingredient preparation**: Basic prep work (e.g., "准备葱姜", "切段", "洗净")
   - **Generic instructions**: Steps that are self-explanatory (e.g., "盛出", "装盘", "趁热食用")
   - **Steps without visual complexity**: Any step where the text alone is sufficient
   
   **Decision process**:
   1. First, evaluate if the step truly benefits from visual demonstration
   2. If yes, then look for a matching image
   3. If no matching image exists or match is uncertain, **skip adding an image** to that step
   4. **Default to NOT adding an image** unless there's a clear benefit
   
   **Extract order from screenshot filenames**:
   - **Identify order patterns**:
     - **Timestamp pattern**: Look for date/time in filename
       - Format examples: `Screenshot 2026-01-30 at 00.09.02.png`, `IMG_20260130_000902.png`
       - Extract: `2026-01-30 00:09:02` → parse as datetime, sort chronologically
       - Earlier timestamp = earlier step
     - **Sequential number pattern**: Look for numbers that increment
       - Format examples: `IMG_7977.PNG`, `IMG_7978.PNG`, `IMG_7979.PNG`
       - Extract: `7977`, `7978`, `7979` → sort numerically
       - Lower number = earlier step (if numbers are sequential)
     - **Explicit step numbers**: Look for step indicators
       - Format examples: `step_1.png`, `photo_1.png`, `image_01.png`
       - Extract: `1`, `2`, `3` → sort numerically
   - **Sort screenshots**:
     - Parse all filenames and extract order information
     - Sort by extracted order (chronological for timestamps, numerical for numbers)
     - Create ordered list: `[screenshot_1, screenshot_2, ..., screenshot_n]`
     - This ordered list represents the sequence of steps in the recipe
   - **Handle edge cases**:
     - If some screenshots have order info and others don't, prioritize those with order info
     - If order information is ambiguous or inconsistent, fall back to content-based matching
     - If no clear order pattern exists, use content-based matching as primary method
   
   **Match images to steps** (order-first, content-verified matching):
   
   **Critical requirement**: Ensure text and image content correspond accurately. Never match an image to a step if the content doesn't match.
   
   **Content verification process**:
   1. **Extract key elements from step text**:
      - Main action/verb (e.g., "切", "炒", "摆", "蒸")
      - Key ingredients/objects (e.g., "鲈鱼", "鸡腿肉", "杏鲍菇")
      - Visual characteristics (e.g., "花刀", "金黄", "薄片", "焦糖色")
      - Cooking state/stage (e.g., "腌制", "焯水", "出锅")
   
   2. **Analyze image content**:
      - Identify what the image actually shows:
        - What ingredients/foods are visible?
        - What cooking action is being performed?
        - What is the cooking state (raw, cooking, finished)?
        - Any specific visual features (cuts, arrangements, colors)?
      - Extract any text visible in the image (subtitles, labels, step numbers)
   
   3. **Match verification criteria** (ALL must be satisfied):
      - **Ingredient match**: The main ingredient(s) in the step text must be visible in the image
      - **Action match**: The action described in the step should be shown or implied in the image
      - **State match**: The cooking state (raw/prep, cooking, finished) should align
      - **Visual feature match**: If step mentions specific visual features (e.g., "花刀", "薄片"), they should be visible
      - **Text cue match**: If image contains step numbers or text, verify they match the step
   
   4. **Matching strategies** (in order of preference):
      - **Filename order match** (HIGHEST PRIORITY): 
        - Extract sequential order from screenshot filenames (timestamps or numbers)
        - Sort screenshots by their order
        - Match first screenshot (by order) to step 1, second to step 2, etc.
        - This is the **strongest signal** when filenames contain clear sequential information
        - Example: `Screenshot 2026-01-30 at 00.09.02.png` → likely step 1, `Screenshot 2026-01-30 at 00.09.22.png` → likely step 2
        - Example: `IMG_7977.PNG` → likely step 1, `IMG_7978.PNG` → likely step 2
      - **Explicit text match**: If image contains step numbers (e.g., "步骤1", "Step 1") or text matching step content, use this as secondary indicator
      - **Content-based match**: Compare extracted step elements with image content (verify filename order match makes sense)
      - **Visual similarity**: Compare visual features mentioned in text with what's shown in image
   
   **Important**: When filename order is available, use it as the primary matching method, but still verify content matches to ensure accuracy.
   
   5. **Rejection criteria** (do NOT match if):
      - Image shows different ingredients than mentioned in step
      - Image shows a different cooking stage (e.g., step says "腌制" but image shows "出锅")
      - Image shows a different action (e.g., step says "切" but image shows "炒")
      - Image appears to be a duplicate or very similar to cover image
      - Image quality is too poor to verify content
      - No clear relationship between step text and image content
   
   6. **Verification workflow**:
      ```
      Step 1: Extract order from filenames
        - Parse all screenshot filenames
        - Extract timestamps or sequential numbers
        - Sort screenshots by order (chronological or numerical)
        - Create ordered list: [screenshot_1, screenshot_2, ..., screenshot_n]
      
      Step 2: Identify steps that need images
        - Evaluate each step: does it need visual demonstration?
        - Create list of steps requiring images: [step_3, step_5, step_7]
      
      Step 3: Match using filename order (primary method)
        - For each step requiring an image:
          a. Determine step number (e.g., step 3 is 3rd step)
          b. Find screenshot at corresponding position in ordered list (e.g., 3rd screenshot → step 3)
          c. Verify content match:
             - Extract key elements from step text
             - Analyze image content
             - Check all match criteria
             - Score the match (0-100)
          d. If match score > 70, assign image to step
          e. If match score ≤ 70, skip this step (don't force match)
      
      Step 4: Fallback matching (if filename order unclear)
        - If filenames don't contain clear order information:
          a. Use explicit text match (step numbers in image)
          b. Use content-based matching
          c. Score and select best match (score > 70)
      
      Step 5: Final verification
        - Double-check: manually verify each match makes sense
        - Ensure no duplicate matches
        - Ensure content truly corresponds
      ```
   
   7. **When in doubt**:
      - If multiple images could match, choose the one with highest content similarity
      - If no image clearly matches a step, **do not force a match** - leave the step without an image
      - If unsure about a match, prefer skipping rather than incorrect matching
      - Ask user for clarification if multiple ambiguous matches exist
   
   **IMPORTANT**: After matching, you should typically have images for only 20-40% of steps (or even fewer). If you find yourself adding images to most steps, reconsider - most steps should remain text-only.
   
   **Process step images automatically** (only for matched steps):
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
   
   **Best practices for step images** (selective approach):
   - **Default to NO image**: Only add an image when it's truly necessary and adds value
   - **Content accuracy is paramount**: Never match an image to a step unless you're confident the content corresponds
   - **Selective addition**: Most steps should remain text-only. Only add images to steps that:
     - Describe visual techniques that are hard to convey in text
     - Show critical visual outcomes
     - Demonstrate complex spatial arrangements
   - **Don't add images to**:
     - Simple text-only steps (e.g., "加盐调味", "搅拌均匀", "腌制10分钟")
     - Standard cooking operations (e.g., "倒入锅中", "大火烧开")
     - Generic instructions (e.g., "盛出", "装盘")
   - **Quality over quantity**: Better to have 2-3 meaningful step images than 10 unnecessary ones
   - **When in doubt, skip**: If unsure whether a step needs an image, **default to NOT adding one**
   - **No forced consistency**: Don't feel obligated to add images to adjacent steps just because one step has an image
   - **Match quality matters**: Only add an image if there's a clear, high-quality match (score > 70)
   
   **Examples of steps that SHOULD have images** (if matching image exists):
   - ✅ Step: "首先把鲈鱼处理干净，开背，改成交叉一字花刀" → Image showing a fish with cross cuts (visual technique)
   - ✅ Step: "杏鲍菇用刮皮刀刨成薄片" → Image showing sliced king oyster mushrooms (specific visual outcome)
   - ✅ Step: "炒至焦糖色" → Image showing caramel-colored food in a pan (critical visual state)
   - ✅ Step: "将鸡肉和杏鲍菇交叉摆放在盘中" → Image showing arranged ingredients (spatial arrangement)
   
   **Examples of steps that should NOT have images** (even if images are available):
   - ❌ Step: "加盐调味" → No image needed (simple text instruction)
   - ❌ Step: "搅拌均匀" → No image needed (standard operation)
   - ❌ Step: "腌制10分钟" → No image needed (time-based, no visual complexity)
   - ❌ Step: "倒入锅中" → No image needed (common action)
   - ❌ Step: "大火烧开" → No image needed (standard cooking instruction)
   - ❌ Step: "盛出装盘" → No image needed (generic instruction)
   
   **Examples of incorrect matches (DO NOT DO)**:
   - ❌ Step: "腌制鸡腿肉" → Image showing finished dish (wrong stage)
   - ❌ Step: "切杏鲍菇" → Image showing chicken (wrong ingredient)
   - ❌ Step: "蒸制" → Image showing frying (wrong cooking method)
   - ❌ Step: "加盐调味" → Image showing final plated dish (step doesn't need image + wrong match)

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
  - Extract sequential order from screenshot filenames (timestamps or numbers)
  - Automatically detect steps that require visual demonstration
  - Match images to steps using filename order as primary indicator, then verify content matches
  - Only add images to steps that truly benefit from visual aid
  - Convert string instructions to objects with `text` and `imageUrl` fields when adding step images
  - Maintain backward compatibility: steps without images remain as strings

- **Nutrition accuracy**:
  - Always add missing ingredients to `calculate_nutrition.py` for future use
  - Use authoritative nutrition databases for ingredient data
  - Document the source of nutrition data in comments if needed

- **Text extraction and expansion**:
  - **Never copy text verbatim from images** - always understand and expand
  - Expand abbreviated terms to full, clear descriptions
  - Fill in implicit information that would be obvious to a cook
  - Make instructions complete sentences that are self-explanatory
  - Clarify cooking methods, heat levels, and timing when mentioned
  - Ensure all text is clear, complete, and easy to understand
  - Maintain accuracy while improving readability
  - Example: "改刀" → "将鲈鱼改成交叉一字花刀，方便入味和蒸制"
  - Example: "腌制" → "加盐、料酒腌制10分钟，使其入味"

- **Error handling**:
  - If recipe images are unclear, ask the user for clarification
  - If ingredient quantities are ambiguous, make reasonable estimates and note them
  - If nutrition calculation fails, investigate the cause (missing ingredients, unit mismatches, etc.)

## Example Workflow

1. User provides 10 screenshots of a recipe video:
   - `Screenshot 2026-01-30 at 00.09.02.png`
   - `Screenshot 2026-01-30 at 00.09.22.png`
   - `Screenshot 2026-01-30 at 00.09.45.png`
   - ... (7 more screenshots with sequential timestamps)
2. **Extract and expand recipe information** (not verbatim copy):
   - **Title**: Image shows "杏鲍菇鸡腿一锅焖" → Use as is (already clear)
   - **Ingredients**: 
     - Image shows "鸡腿肉 400g" → Expand to "去骨鸡腿肉 400克"
     - Image shows "杏鲍菇 300g" → Use as is
     - Image shows "黄酒" → Expand to "黄酒 30毫升"
     - Image shows "黑胡椒" → Expand to "黑胡椒 适量"
   - **Instructions** (8 steps, expanded from brief image text):
     - Image step 1: "杏鲍菇刨片" → Expand to "杏鲍菇用刮皮刀刨成薄片，备用"
     - Image step 2: "腌制" → Expand to "鸡腿肉加盐、黑胡椒腌制10分钟，使其入味"
     - Image step 3: "铺食材" → Expand to "将腌制好的鸡肉和姜片铺在锅底"
     - Image step 4: "倒酒" → Expand to "倒入黄酒，增加香味"
     - Image step 5: "焖制" → Expand to "大火烧开后转小火焖制15分钟"
     - Image step 6: "撒蒜酥" → Expand to "出锅前撒上蒜酥，增加口感"
     - Image step 7: "装盘" → Expand to "盛出装盘，趁热食用"
     - Image step 8: "完成" → Expand to "完成，即可享用"
3. Determine next ID: 35
4. Create recipe entry with `imageUrl: "images/recipe_35.png"`
5. Select first screenshot (by timestamp) as cover, save as `images/recipe_35.png`
6. **Extract order from remaining 9 screenshots**:
   - Parse filenames: extract timestamps `00.09.02`, `00.09.22`, `00.09.45`, etc.
   - Sort by timestamp (chronological order)
   - Ordered list: [screenshot_1, screenshot_2, ..., screenshot_9]
   - Note: screenshot_1 corresponds to step 1, screenshot_2 to step 2, etc.
7. **Analyze remaining 9 images for step matching** (selective approach):
   - **First, evaluate which steps actually need images**:
     - Step 1: "杏鲍菇用刮皮刀刨成薄片" → ✅ NEEDS image (visual technique)
     - Step 2: "加盐、黑胡椒腌制10分钟" → ❌ NO image needed (simple text instruction)
     - Step 3: "铺鸡肉和姜片" → ✅ NEEDS image (spatial arrangement)
     - Step 4: "倒入黄酒" → ❌ NO image needed (standard operation)
     - Step 5: "大火烧开转小火" → ❌ NO image needed (standard cooking)
     - Step 6: "撒蒜酥" → ✅ NEEDS image (visual arrangement)
     - Step 7: "盛出装盘" → ❌ NO image needed (generic instruction)
     - Step 8: "趁热食用" → ❌ NO image needed (generic instruction)
   
   - **Match using filename order** (primary method):
     - Step 1 needs image → Use screenshot_1 (first in ordered list)
       - Verify: screenshot_1 shows sliced mushrooms → ✅ Match confirmed
     - Step 3 needs image → Use screenshot_3 (third in ordered list)
       - Verify: screenshot_3 shows chicken and ginger arranged → ✅ Match confirmed
     - Step 6 needs image → Use screenshot_6 (sixth in ordered list)
       - Verify: screenshot_6 shows garlic crisp being sprinkled → ✅ Match confirmed
   
   - **Result**: Only 3 out of 8 steps get images (not all steps need images!)
   - Automatically move/rename matched images: 
     - `Screenshot 2026-01-30 at 00.09.02.png` → `images/recipe_35_step_1.png`
     - `Screenshot 2026-01-30 at 00.09.45.png` → `images/recipe_35_step_3.png`
     - `Screenshot 2026-01-30 at 00.10.15.png` → `images/recipe_35_step_6.png`
   - Update `instructions` array: convert only the 3 matching steps to objects with `imageUrl`
   - Leave other steps as plain text strings (no forced matches)
7. Calculate nutrition → warnings about "去骨鸡腿肉", "杏鲍菇", "黄酒", "黑胡椒"
8. Add these ingredients to `calculate_nutrition.py` with accurate nutrition data
9. Recalculate nutrition → update recipe
10. Verify all fields are complete, including step images

## Notes

- The `salt` field in nutrition represents **salt content in grams**, calculated from sodium content
- Conversion: salt (g) = sodium (mg) / 1000 * 2.54
- Some ingredients may have special units (个, 头, 瓣, 滴) that require special handling in `calculate_nutrition.py`
- Always preserve existing recipes when updating `recipes.json` - never overwrite or delete existing entries
