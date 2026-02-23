# 临时文件目录

此目录用于存放**临时文件和日志**，定期清理。

## 包含内容

- `temp_scripts/` - 测试脚本、验证脚本等临时Python文件
- `test_logs/` - 测试运行日志
- `build_cache/` - 构建缓存文件

## 清理策略

运行此命令定期清理：
```bash
python cleanup_disposable.py
```

## 规则

❌ **不放在主文件夹的文件：**
- 验证脚本 (verify_*.py, test_*.py)
- 构建脚本 (build_*.py)
- 临时日志文件
- PyInstaller 缓存

✅ **可以放在主文件夹的文件：**
- `koto_app.py` - 主应用
- `launch.py` - 启动器
- `*.bat`, `*.vbs` - 启动脚本
- `README.md` - 文档
