# 食谱管理系统

一个功能完整、界面美观的食谱管理系统，支持分类浏览、全文搜索和详细食谱展示。

## 功能特性

### 🏠 主页功能
- **分类浏览**：通过分类标签快速筛选食谱（中餐、西餐、甜点、饮品等）
- **全文搜索**：实时搜索食谱标题、食材、制作方法和分类
- **搜索结果高亮**：匹配的关键词会高亮显示
- **响应式设计**：完美适配手机、平板和桌面设备

### 📄 详情页功能
- **完整信息展示**：食谱标题、描述、主图、食材清单、制作步骤
- **清晰的布局**：食材以表格形式展示，制作步骤有序编号
- **导航功能**：快速返回主页或打印食谱

## 项目结构

```
recipe_set/
├── index.html              # 主页
├── recipe_detail.html      # 食谱详情页
├── recipes.json            # 食谱数据源
├── css/
│   └── style.css          # 主样式文件
├── js/
│   └── main.js            # 主JavaScript文件
├── images/                # 图片资源文件夹（可选）
└── README.md              # 项目说明文档
```

## 使用方法

### 1. 直接打开
- 使用现代浏览器（Chrome、Firefox、Safari、Edge）直接打开 `index.html`
- 注意：由于使用了 `fetch` API 加载 JSON 文件，需要通过 HTTP 服务器运行，不能直接使用 `file://` 协议

### 2. 使用本地服务器（推荐）

#### 方法一：使用 Python
```bash
# Python 3
python -m http.server 8000

# Python 2
python -m SimpleHTTPServer 8000
```
然后在浏览器中访问 `http://localhost:8000`

#### 方法二：使用 Node.js
```bash
# 安装 http-server
npm install -g http-server

# 运行服务器
http-server -p 8000
```

#### 方法三：使用 VS Code
- 安装 "Live Server" 扩展
- 右键点击 `index.html`，选择 "Open with Live Server"

## 数据结构

`recipes.json` 文件包含所有食谱数据，每个食谱对象包含以下字段：

```json
{
  "id": 1,                    // 唯一标识符
  "title": "食谱名称",         // 食谱标题
  "category": ["分类1", "分类2"], // 分类数组
  "imageUrl": "图片路径",      // 图片路径（可选）
  "description": "描述",       // 食谱描述（可选）
  "ingredients": [            // 食材数组
    {
      "name": "食材名",
      "quantity": 数量,
      "unit": "单位"
    }
  ],
  "instructions": [           // 制作步骤数组
    "步骤1",
    "步骤2"
  ]
}
```

## 添加新食谱

1. 打开 `recipes.json` 文件
2. 在数组中添加新的食谱对象
3. 确保 `id` 唯一
4. 保存文件后刷新浏览器即可看到新食谱

## 自定义样式

所有样式都在 `css/style.css` 文件中，使用 CSS 变量便于自定义：

- `--primary-color`: 主色调
- `--secondary-color`: 次要色调
- `--accent-color`: 强调色
- `--dark-color`: 深色文字
- `--light-color`: 浅色背景

修改这些变量即可快速改变整体配色方案。

## 浏览器兼容性

- Chrome/Edge (最新版本)
- Firefox (最新版本)
- Safari (最新版本)
- 移动端浏览器

## 技术栈

- **HTML5**: 语义化标签
- **CSS3**: Flexbox、Grid、CSS变量、响应式设计
- **JavaScript (ES6+)**: Fetch API、事件处理、DOM操作

## 注意事项

1. 图片资源：当前使用 emoji 作为占位符，如需使用真实图片，请将图片放入 `images/` 文件夹，并在 `recipes.json` 中更新 `imageUrl` 路径
2. 数据加载：确保 `recipes.json` 文件与 HTML 文件在同一服务器上
3. 搜索功能：支持中文搜索，实时匹配
4. 分类筛选：点击分类按钮可快速筛选，支持多分类

## 未来扩展

- [ ] 添加图片上传功能
- [ ] 实现食谱收藏功能
- [ ] 添加用户评价系统
- [ ] 支持食谱分享功能
- [ ] 添加营养成分计算
- [ ] 实现食谱编辑功能

## 许可证

本项目仅供学习和个人使用。
