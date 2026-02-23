# 🚀 Koto 应用 - Windows 安装包生成指南

## 📋 概述

本指南将帮助您为 Koto 应用生成可在**任何新 Windows 电脑**上使用的独立安装包。

**特点**:
- ✅ 无需安装 Python
- ✅ 无需额外依赖
- ✅ 一键启动
- ✅ 支持离线使用

---

## 📦 生成安装包

### 方式 1: 使用批处理脚本 (推荐)

**最简单的方式 - 适合大多数用户**

```bash
1. 用文件管理器打开 Koto 项目文件夹
2. 找到 build_installer.bat 文件
3. 双击运行
4. 等待完成（通常 5-10 分钟）
5. 自动打开 installer 文件夹
```

### 方式 2: 使用 PowerShell 脚本

**更多控制选项**

```powershell
# 打开 PowerShell（管理员）
# 运行以下命令：

Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope CurrentUser -Force
cd C:\Users\YourUsername\Desktop\Koto
.\build_installer.ps1
```

### 方式 3: 使用 Python 直接运行

**完全手动控制**

```bash
cd C:\Users\YourUsername\Desktop\Koto
python build_installer.py
```

---

## 🎯 安装包说明

### 生成的文件

构建完成后，`installer` 文件夹中会包含：

#### 1. **Koto_v1.0.0_Portable.zip** (推荐)
```
文件: Koto_v1.0.0_Portable.zip
大小: ~100-200 MB
说明: 便携式包，解压即用

使用方式:
1. 将文件解压到任意目录
2. 双击 run.bat 启动应用
3. 或直接双击 Koto.exe

优点:
✓ 无需管理员权限
✓ 可复制到 U 盘
✓ 支持离线使用
✓ 多个版本共存
```

#### 2. **Koto_v1.0.0_Installer.exe** (如果安装了 NSIS)
```
文件: Koto_v1.0.0_Installer.exe
大小: ~80-150 MB
说明: 向导式安装程序

使用方式:
1. 运行 .exe 文件
2. 按照向导完成安装
3. 自动创建开始菜单快捷方式
4. 自动添加到控制面板卸载列表

优点:
✓ 标准安装体验
✓ 自动创建快捷方式
✓ 注册到系统
✓ 方便卸载
```

#### 3. **Koto\Koto.exe** (单个可执行文件)
```
文件: installer\Koto_v1.0.0\Koto.exe
说明: 独立可执行文件

使用方式:
直接双击启动

注意:
⚠️ 需要所有依赖已正确打包
⚠️ 第一次启动稍慢
```

---

## 🖥️ 部署到新电脑

### 场景 1: 单个电脑

```
1. 将 Koto_v1.0.0_Portable.zip 复制到目标电脑
2. 解压文件
3. 双击 run.bat 或 Koto.exe
4. 完成！
```

### 场景 2: 多个电脑

```
方案 A: 使用 U 盘
1. 将便携式包复制到 U 盘
2. 在任何电脑上插入 U 盘
3. 解压并运行

方案 B: 使用网络共享
1. 将包上传到公司网络共享
2. 需要时下载使用
3. 支持多人同时使用

方案 C: 使用安装程序
1. 将 .exe 安装程序分发
2. 用户自行运行安装
3. 统一管理，易于卸载
```

### 场景 3: 批量部署

```
使用 PowerShell 批处理脚本:

# 创建 deploy.ps1
function Install-Koto {
    param(
        [string]$SourcePath,
        [string]$DestPath = "C:\Program Files\Koto"
    )
    
    Extract-Zip -Source $SourcePath -Destination $DestPath
    Start-Process "$DestPath\Koto.exe"
}

# 部署到多个位置
Get-ChildItem -Path "\\server\shared" -Filter "*.zip" | ForEach-Object {
    Install-Koto -SourcePath $_.FullName
}
```

---

## ⚙️ 系统要求

### 最低要求
- **操作系统**: Windows 7 SP1+
- **内存**: 1 GB RAM
- **磁盘**: 200 MB 可用空间
- **其他**: 无需 Python 或其他依赖

### 推荐配置
- **操作系统**: Windows 10/11
- **内存**: 4+ GB RAM
- **磁盘**: 500 MB+ 可用空间
- **网络**: 互联网连接（用于某些功能）

---

## 🔧 高级选项

### 自定义生成过程

#### 仅生成便携式包
```bash
python build_installer.py --skip-nsis
```

#### 跳过依赖安装
```bash
python build_installer.py --skip-install
```

#### 指定输出目录
```bash
python build_installer.py --output D:\Packages
```

#### 包含调试信息
```bash
python build_installer.py --verbose
```

### 自定义应用信息

编辑 `build_installer.py` 中的以下常量：

```python
APP_NAME = "Koto"           # 应用名称
APP_VERSION = "1.0.0"       # 版本号
APP_DESCRIPTION = "..."     # 描述
AUTHOR = "Koto Team"        # 作者
COMPANY = "Koto"            # 公司名
```

---

## 🐛 故障排查

### 问题 1: "Python 未找到"

**解决方案**:
```bash
1. 安装 Python 3.8 或更高版本
2. 访问 https://www.python.org/downloads/
3. 安装时勾选 "Add Python to PATH"
4. 重启命令行后再试
```

### 问题 2: "PyInstaller 安装失败"

**解决方案**:
```bash
pip install --upgrade pip
pip install pyinstaller --no-cache-dir
```

### 问题 3: "NSIS 未找到"

**解决方案**:
```
这是可选的，只会跳过 .exe 安装程序生成
如果需要，从 https://nsis.sourceforge.io 下载安装
```

### 问题 4: "权限被拒绝"

**解决方案**:
```powershell
# 在 PowerShell 中运行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 然后再运行构建脚本
```

### 问题 5: 构建花费时间太长

**说明**:
- 首次构建: 10-15 分钟 (正常)
- 后续构建: 5-10 分钟 (已缓存)
- 包含签名: 可能更长

**解决方案**:
```bash
# 删除缓存
rmdir /s build dist
# 再次运行构建
```

---

## 📊 构建统计

### 输出文件大小

```
Koto.exe (可执行文件)     : ~80-120 MB
ZIP 包 (便携式)          : ~2-40 MB (已压缩)
EXE 安装程序            : ~80-120 MB
```

### 构建时间

```
依赖安装      : ~2-3 分钟
编译可执行文件  : ~3-5 分钟
打包          : ~1-2 分钟
───────────────────────
总计          : ~8-12 分钟
```

---

## 🚀 部署最佳实践

### 1. 验证包的完整性

```bash
# 检查文件完整性
certutil -hashfile Koto_v1.0.0_Portable.zip SHA256

# 保存哈希值供验证
Get-FileHash installer\*.zip | Export-Csv checksums.csv
```

### 2. 创建安装说明

在 `installer\Koto_v1.0.0\` 文件夹中已自动生成 `README.txt`，包含：
- 快速开始指南
- 系统要求
- 功能列表
- 常见问题
- 快捷方式创建脚本

### 3. 测试部署

```bash
# 在隔离环境中测试
1. 创建虚拟机或在另一个电脑上测试
2. 解压/安装包
3. 启动应用
4. 测试基本功能
```

### 4. 版本管理

```
推荐文件命名:
Koto_v1.0.0_Portable.zip      (版本 1.0.0)
Koto_v1.0.1_Portable.zip      (版本 1.0.1)
Koto_v1.1.0_Portable.zip      (版本 1.1.0)

配置版本号在 build_installer.py 中
```

### 5. 更新策略

```
方案 A: 完全替换
1. 备份配置文件（config 文件夹）
2. 删除旧版本
3. 安装新版本
4. 恢复配置文件

方案 B: 并行安装
1. 将新版本解压到不同目录
2. 保留旧版本用于备份
3. 逐步迁移用户
```

---

## 📞 支持

### 生成的文件

| 文件 | 用途 |
|------|------|
| build_installer.py | Python 构建脚本 |
| build_installer.bat | 批处理自动化脚本 |
| build_installer.ps1 | PowerShell 脚本 |
| installer/BUILD_SUMMARY.txt | 构建详细信息 |

### 查看日志

```
构建过程中生成的日志:
build_YYYYMMDD_HHMMSS.log

查找最近的日志:
dir /od build_*.log
```

---

## 🎓 常见任务

### 任务 1: 快速生成安装包

```bash
# 最快的方式
double-click build_installer.bat
```

### 任务 2: 修改版本号

```python
# 编辑 build_installer.py

APP_VERSION = "1.0.1"  # 改为新版本
```

### 任务 3: 包含自定义文件

```python
# 编辑 COLLECT_DIRS 列表

COLLECT_DIRS = [
    "config",
    "assets",
    "web",
    "models",
    "docs",
    "my_custom_dir",  # 添加自定义目录
]
```

### 任务 4: 修改应用图标

```bash
1. 准备 icon.ico 文件 (推荐 256x256 像素)
2. 放在 assets 文件夹中
3. 重新构建
```

### 任务 5: 添加启动参数

编辑生成的 `run.bat`:
```batch
@echo off
start "" "!SCRIPT_DIR!Koto.exe" --debug --port 5001
```

---

## 📝 检查清单

使用此清单验证安装包：

- [ ] 生成的可执行文件能正常启动
- [ ] 应用基本功能正常
- [ ] 配置文件可正常加载
- [ ] 日志文件可正常写入
- [ ] 在无 Python 的电脑上可运行
- [ ] 快捷方式正常工作
- [ ] 卸载程序正常卸载（如使用 .exe）

---

## 🎉 成功标志

安装包生成完成后，您应该看到：

```
✅ 构建完成！
📁 安装包位置: C:\Users\你的用户名\Desktop\Koto\installer

Windows 文件管理器打开，显示:
├── Koto_v1.0.0_Portable.zip
├── Koto_v1.0.0_Installer.exe (可选)
├── BUILD_SUMMARY.txt
└── Koto_v1.0.0/
    ├── Koto.exe
    ├── run.bat
    ├── README.txt
    └── 其他支持文件...
```

---

**现在您可以将这些文件分发到任何 Windows 电脑了！** 🚀

有任何问题，详见生成的 `README.txt` 或执行日志文件。
