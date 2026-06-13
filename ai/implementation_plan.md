# 数据库操作与 SiteNav 逻辑优化计划

本计划旨在解决在分析 `sitenav` 模块以及通用数据库操作类时发现的代码逻辑缺陷和数据库一致性问题。

## 需要用户评审的项

> [!IMPORTANT]
> - **SQL 插入语句动态构建**：我们将修改 `SiteItem.add` 和 `DataRecorder.add` 中的 `INSERT` 查询构造方式，使其与 `kwargs` 传入的实际参数动态对齐。这可以避免因列与占位符数量不匹配导致的运行时 SQL 错误。
> - **递归/级联删除子节点**：目前在 SiteNav 中删除目录节点会导致其子节点在数据库中变成“孤儿节点”。我们建议在 Python 逻辑层实现递归级联删除，以确保数据的引用完整性。
> - **统一树形构建逻辑**：我们将统一 API 路由（`route.py`）和静态 JS 生成器（`generate_js.py`）中的建树算法，以避免孤儿节点在 API 树中正常显示却在静态 JS 中被无声丢弃的数据不一致问题。

## 拟议的修改

---

### 组件: 网站导航 (source/sitenav)

#### [MODIFY] [module.py](file:///d:/Workspaces/Github/XHS-Downloader/source/sitenav/module.py)
- 重构 `SiteItem.add`，使插入的 `columns` 和 `placeholders` 能够根据 `kwargs` 传入的字段（且属于 `DATA_TABLE` 定义的有效字段）动态生成。
- 更新 `SiteItem.delete`，实现递归删除当前节点的所有子节点（即 `pId` 等于当前节点 `id` 的所有记录），保证级联删除，防止产生数据库孤儿节点。

#### [MODIFY] [generate_js.py](file:///d:/Workspaces/Github/XHS-Downloader/source/sitenav/generate_js.py)
- 重构 `build_tree`，使其对根节点的判定逻辑与 API 保持一致（如果 `pId == 0` 或父节点不在映射字典中，则均视为根节点进行挂载）。

---

### 组件: 数据记录模块 (source/module)

#### [MODIFY] [recorder.py](file:///d:/Workspaces/Github/XHS-Downloader/source/module/recorder.py)
- 重构 `DataRecorder.add`，动态对齐插入字段与值，避免因缺失某些可选字段时抛出 `KeyError` 或列/值不匹配的错误。

---

## 验证计划

### 自动化/单元测试
- 在 `scratch/` 目录下编写测试脚本 `test_db_logic.py`，验证：
  1. 传入部分可选字段时，`add` 方法是否能正确执行，无 SQL 报错。
  2. 插入目录树并删除父节点后，子节点是否已被级联删除。
  3. 孤儿节点在 JSON 树和 JS 输出格式中是否能统一作为根元素保留显示。

### 手动验证
- 启动 FastAPI 服务器。
- 调用 `/sites` 的 POST 端点保存站点项。
- 访问 `/sites/tree` API 端点，确认树状数据结构是否正确。
