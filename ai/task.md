# 任务清单: SiteNav 与数据库优化

## 阶段 1: 健全 SQL 插入助手
- [ ] 重构 [SiteItem.add](file:///d:/Workspaces/Github/XHS-Downloader/source/sitenav/module.py#L60)，使列名、占位符和传入的值动态对齐。
- [ ] 重构 [DataRecorder.add](file:///d:/Workspaces/Github/XHS-Downloader/source/module/recorder.py#L121)，动态对齐字段与值，防止缺失参数报错。

## 阶段 2: 级联节点删除与统一建树逻辑
- [ ] 更新 [SiteItem.delete](file:///d:/Workspaces/Github/XHS-Downloader/source/sitenav/module.py#L82)，使其支持递归删除所有子节点。
- [ ] 重构 [generate_js.py](file:///d:/Workspaces/Github/XHS-Downloader/source/sitenav/generate_js.py) 中的 `build_tree` 函数，统一根节点识别逻辑，合理保留无父节点的孤儿节点。
- [ ] 清理无用的 [site_nav.py](file:///d:/Workspaces/Github/XHS-Downloader/source/sitenav/site_nav.py) 文件，并在 [__init__.py](file:///d:/Workspaces/Github/XHS-Downloader/source/sitenav/__init__.py) 中移除相关导出。

## 阶段 3: 功能验证
- [ ] 在 `scratch/test_db_logic.py` 中编写测试脚本，验证 SQL 安全插入及级联删除逻辑。
- [ ] 运行 FastAPI 接口验证 `/sites/tree` API 输出。
