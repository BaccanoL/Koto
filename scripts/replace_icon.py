#!/usr/bin/env python3
"""
图标替换工具 - 将新图标转换为所需格式并替换
"""
import sys
from pathlib import Path
from PIL import Image

def convert_and_replace_icon(source_image_path: str):
    """将源图标转换为PNG和ICO格式并替换现有图标"""
    source_path = Path(source_image_path)
    
    if not source_path.exists():
        print(f"❌ 错误: 找不到文件 {source_path}")
        return False
    
    print(f"📷 正在处理图标: {source_path}")
    
    try:
        # 打开源图像
        img = Image.open(source_path)
        print(f"   原始尺寸: {img.size}")
        print(f"   格式: {img.format}")
        
        # 转换为RGBA模式（支持透明度）
        if img.mode != 'RGBA':
            print(f"   转换模式: {img.mode} -> RGBA")
            img = img.convert('RGBA')
        
        # 调整大小为256x256（如果需要）
        if img.size != (256, 256):
            print(f"   调整大小: {img.size} -> (256, 256)")
            img = img.resize((256, 256), Image.Resampling.LANCZOS)
        
        # 保存为PNG
        assets_dir = Path(__file__).parent / "assets"
        assets_dir.mkdir(exist_ok=True, parents=True)
        
        png_path = assets_dir / "koto_icon.png"
        ico_path = assets_dir / "koto_icon.ico"
        
        # 备份现有图标
        if png_path.exists():
            backup_path = assets_dir / "koto_icon.png.backup"
            png_path.rename(backup_path)
            print(f"   ✅ 已备份原PNG: {backup_path.name}")
        
        if ico_path.exists():
            backup_path = assets_dir / "koto_icon.ico.backup"
            ico_path.rename(backup_path)
            print(f"   ✅ 已备份原ICO: {backup_path.name}")
        
        # 保存新PNG
        img.save(str(png_path), 'PNG')
        print(f"   ✅ 已保存PNG: {png_path}")
        
        # 生成多尺寸ICO
        img.save(str(ico_path), format='ICO', sizes=[
            (256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)
        ])
        print(f"   ✅ 已保存ICO: {ico_path}")
        
        print("\n🎉 图标替换完成！")
        print("   请重启Koto应用以应用新图标")
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python replace_icon.py <图标文件路径>")
        print("支持的格式: PNG, JPG, ICO, SVG等")
        print("\n示例: python replace_icon.py new_icon.png")
        sys.exit(1)
    
    source_file = sys.argv[1]
    success = convert_and_replace_icon(source_file)
    sys.exit(0 if success else 1)
